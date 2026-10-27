"""VakCare backend configuration package."""

# Fallback for serverless environments (like Vercel Amazon Linux) where mysqlclient C-extensions
# may not be compiled: safely use PyMySQL as the MySQLdb driver if native MySQLdb is unavailable.
try:
    import MySQLdb  # noqa: F401
except ImportError:
    try:
        import pymysql
        pymysql.version_info = (2, 2, 0, "final", 0)
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
