import os
import psycopg2
import psycopg2.extras
from sshtunnel import SSHTunnelForwarder


from models import Relocation

def get_db_connection():
    """Establishes a connection to the PostgreSQL database via an SSH tunnel."""
    
    ssh_host = os.getenv("SSH_HOST")
    ssh_port = int(os.getenv("SSH_PORT", 22))
    ssh_user = os.getenv("SSH_USERNAME")
    ssh_private_key_path = os.getenv("SSH_PRIVATE_KEY")
    ssh_key_password = os.getenv("SSH_PRIVATE_KEY_PASSWORD")

    print(f"DEBUG: Path for SSH_PRIVATE_KEY is: '{ssh_private_key_path}'")

    if not ssh_private_key_path:
        raise ValueError("SSH_PRIVATE_KEY environment variable not set or empty. Please check your .env file and how it's loaded.")
    
    if not os.path.isfile(ssh_private_key_path):
        raise FileNotFoundError(f"The SSH private key file was not found at the specified path: {ssh_private_key_path}")

    db_host = os.getenv("DB_HOST_REMOTE")
    db_port = int(os.getenv("DB_PORT_REMOTE", 5432))
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")

    tunnel = SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_user,
        ssh_pkey=ssh_private_key_path,
        ssh_password=ssh_key_password,
        remote_bind_address=(db_host, db_port)
    )
    
    tunnel.start()
    
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        user=db_user,
        password=db_password,
        dbname=db_name
    )
    
    return conn, tunnel


def get_available_relocations() -> list[dict]:
    """
    Returns a list of all available relocations from the database.
    This tool doesn't require any input.
    """
    conn, tunnel = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql_query = """
                select e.id as id, sn as surname, gn as given_name, cn as complete_name, coalesce(e.uid, e.pro_email_adress, e.perso_email_adress) as email, TO_CHAR(ends, 'DD/MM/YYYY') as relocation_end_date, es.label as relocation_status, TO_CHAR(e.mtime, 'DD/MM/YYYY HH24:MI:SS') as relocation_last_update 
                from application.expat e join application.expat_status es on e.ref_expat_status=es.id 
                where es.label='En cours' and (e.uid is not null or e.pro_email_adress is not null or e.perso_email_adress is not null)
                order by e.mtime desc;
            """
            print(f"agent_db_tools:get_available_relocations: Executing SQL query: {sql_query}")
            cur.execute(sql_query)
            relocations_db = cur.fetchall()
            
            relocations = [Relocation(**dict(r)) for r in relocations_db]
            return relocations
    finally:
        conn.close()
        tunnel.stop()


def get_relocation_status_by_id(relocation_id: int) -> list[dict]:
    """
    Gets the status of a relocation based on its ID from the database.
    """
    conn, tunnel = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql_query = """
                select e.id as id, sn as surname, gn as given_name, cn as complete_name, coalesce(e.uid, e.pro_email_adress, e.perso_email_adress) as email, TO_CHAR(ends, 'DD/MM/YYYY') as relocation_end_date, es.label as relocation_status, TO_CHAR(e.mtime, 'DD/MM/YYYY HH24:MI:SS') as relocation_last_update 
                from application.expat e join application.expat_status es on e.ref_expat_status=es.id 
                where e.id = %s and (e.uid is not null or e.pro_email_adress is not null or e.perso_email_adress is not null)
                order by e.mtime desc;
            """
            print(f"agent_db_tools:get_relocation_status_by_id: Executing SQL query: {sql_query}")
            cur.execute(sql_query, (relocation_id,))
            relocations_db = cur.fetchall()

            relocations = [Relocation(**dict(r)) for r in relocations_db]
            return relocations

    finally:
        conn.close()
        tunnel.stop()


def get_relocation_status_by_name(expat_name: str) -> list[dict]:
    """
    Gets the status of one or several relocations based on the expat name from the database.
    """
    conn, tunnel = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            search_term = f"%{expat_name.lower()}%"
            sql_query = """
                SELECT e.id as id, e.gn as given_name, e.sn as surname, e.cn as complete_name, coalesce(e.uid, e.pro_email_adress, e.perso_email_adress) as email, TO_CHAR(ends, 'DD/MM/YYYY') as relocation_end_date, es.label as relocation_status, TO_CHAR(e.mtime, 'DD/MM/YYYY HH24:MI:SS') as relocation_last_update 
                from application.expat e join application.expat_status es on e.ref_expat_status=es.id
                WHERE lower(e.gn) LIKE %s OR lower(e.sn) LIKE %s OR lower(e.cn) LIKE %s and (e.uid is not null or e.pro_email_adress is not null or e.perso_email_adress is not null)
                """
            print(f"agent_db_tools:get_relocation_status_by_name: Executing SQL query: {sql_query}")
            cur.execute(sql_query, (search_term, search_term, search_term))
            relocations_db = cur.fetchall()

            relocations = [Relocation(**dict(r)) for r in relocations_db]

            return relocations
    finally:
        conn.close()
        tunnel.stop() 