import argparse
import sys
from sqlalchemy import text

# Reuse application utilities
from app.repositories.chatbot_db_util import ChatbotDbUtil
from app.repositories.app_db_util import AppDbUtil


def main():
    parser = argparse.ArgumentParser(description="Inspect Payments table for a chatbot's target DB")
    parser.add_argument("--chatbot-id", required=True, help="Chatbot ID to read DB config from")
    parser.add_argument("--table", default="Payments", help="Table name to inspect (default: Payments)")
    parser.add_argument("--schema", default=None, help="Override schema name (uses chatbot.schema_name if not provided)")
    parser.add_argument("--top", type=int, default=20, help="Number of sample rows to fetch (default: 20)")
    parser.add_argument("--chatbot-meta-db-url", default="postgresql://postgres:postgres@localhost:5432/seshu_bot", help="Postgres URL where chatbots table lives")
    args = parser.parse_args()

    cb_util = ChatbotDbUtil(db_url=args.chatbot_meta_db_url)
    chatbot = cb_util.get_chatbot(args.chatbot_id)
    if not chatbot:
        print(f"ERROR: Chatbot not found: {args.chatbot_id}")
        sys.exit(2)

    db_url = chatbot.get("db_url")
    schema_name = args.schema or chatbot.get("schema_name")

    if not db_url:
        print("ERROR: Chatbot has no db_url configured")
        sys.exit(2)

    app_db = AppDbUtil(db_url=db_url)

    # Compose fully-qualified name depending on schema availability (for MSSQL/Postgres)
    # MSSQL/Postgres safe qualification
    qualified = f"[{schema_name}].[{args.table}]" if (schema_name and 'mssql' in str(app_db.db_engine.url)) else (
        f'"{schema_name}"."{args.table}"' if schema_name else args.table
    )

    # Row count
    try:
        count_sql = f"SELECT COUNT(*) AS cnt FROM {qualified};"
        with app_db.db_engine.connect() as conn:
            row = conn.execute(text(count_sql)).fetchone()
            total = row[0] if row else 0
        print(f"Row count in {qualified}: {total}")
    except Exception as e:
        print(f"ERROR counting rows in {qualified}: {e}")
        sys.exit(1)

    # Column list
    columns = []
    try:
        from sqlalchemy import inspect
        insp = inspect(app_db.db_engine)
        tbl = args.table
        cols = insp.get_columns(tbl, schema=schema_name)
        columns = [c["name"] for c in cols]
        print(f"Columns ({len(columns)}): {columns}")
    except Exception as e:
        print(f"WARN: Could not read column metadata: {e}")

    # Sample rows
    if locals().get("total", 0):
        try:
            is_mssql = "mssql" in str(app_db.db_engine.url)
            top_clause = f"TOP {args.top} " if is_mssql else ""
            order_by = "ORDER BY 1 DESC" if is_mssql else ""
            limit_clause = "" if is_mssql else f" LIMIT {args.top}"
            sample_sql = f"SELECT {top_clause}* FROM {qualified} {order_by}{limit_clause}"
            with app_db.db_engine.connect() as conn:
                res = conn.execute(text(sample_sql)).fetchall()
                print(f"Sample {min(len(res), args.top)} rows:")
                for i, r in enumerate(res[:args.top], 1):
                    # Convert Row to dict safely
                    try:
                        rec = dict(r._mapping)
                    except Exception:
                        rec = dict(r)
                    print({k: rec[k] for k in list(rec.keys())[:10]})
        except Exception as e:
            print(f"ERROR fetching sample rows: {e}")


if __name__ == "__main__":
    main()


