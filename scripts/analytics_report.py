import clickhouse_connect
from tabulate import tabulate
from app.core.config import settings

def run_report():
    client = clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DB
    )

    query = """
    SELECT 
        virtual_key_id,
        count() AS total_reqs,
        sum(is_fallback) AS fallback_count,
        sum(prompt_tokens) AS prompt_toks,
        sum(completion_tokens) AS compl_toks,
        sum(total_tokens) AS total_toks,
        round(sum(cost_usd), 4) AS cost_usd,
        round(avg(latency_ttft_ms), 1) AS avg_ttft_ms,
        quantile(0.99)(latency_total_ms) AS p99_latency_ms
    FROM ai_gateway.request_telemetry
    GROUP BY virtual_key_id
    ORDER BY cost_usd DESC
    LIMIT 15;
    """

    res = client.query(query)
    headers = [
        "Virtual Key", "Total Reqs", "Fallbacks", "Prompt Toks",
        "Compl Toks", "Total Toks", "Cost (USD)", "Avg TTFT", "P99 Latency"
    ]
    print("\n==================== TENANT USAGE & COST ATTRIBUTION ====================")
    print(tabulate(res.result_rows, headers=headers, tablefmt="fancy_grid"))
    print("=========================================================================\n")

if __name__ == "__main__":
    run_report()
