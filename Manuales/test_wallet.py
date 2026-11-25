import oracledb
import os

# $env:TNS_ADMIN = "D:\oracle\waldec25"
# echo $env:TNS_ADMIN
# export TNS_ADMIN=/opt/oracle/wallets/waldec25
# SET TNS_ADMIN=/opt/oracle/wallets/waldec25

os.environ['TNS_ADMIN'] = r'D:\oracle\waldec25'
os.environ['ORACLE_HOME'] = r'D:\softapps\ora21cli\oraclient'

try:
    oracledb.init_oracle_client()
    # print(f"os.environ['TNS_ADMIN']  {os.environ['TNS_ADMIN']} ")
    # print(f"os.environ['ORACLE_HOME']  {os.environ['ORACLE_HOME']} ")
    pool = oracledb.create_pool(
        dsn='STAR_BI_DWH',
        min=2,
        max=10,
        increment=2,
        getmode=oracledb.POOL_GETMODE_WAIT,
        wait_timeout=30,
        timeout=30,
        max_lifetime_session=1800,
        ping_interval=60,
        externalauth=True,
        homogeneous=False,
    )
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(1) +145 FROM BI_DWH.BDW_LISTA_ARCHIVO_TRAZA_TMP")
            result = cursor.fetchone()
            print("Resultado:", result)
except oracledb.DatabaseError as e:
    error, = e.args
    print("Error Oracle:", error.message)
except Exception as e:
    print("Error general:", str(e))
print("ENDLE")
