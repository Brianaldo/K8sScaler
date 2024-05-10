from prometheus.client import PrometheusClient

if __name__ == '__main__':
    print(PrometheusClient.fetch_cpu_usage())