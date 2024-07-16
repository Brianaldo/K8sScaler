import concurrent.futures
from datetime import datetime

from prometheus_api_client import PrometheusConnect
from prometheus_api_client.utils import parse_datetime


class MetricsFetcher:
    def __init__(self, prometheus_url: str):
        self.prometheus = PrometheusConnect(
            url=prometheus_url, disable_ssl=True
        )

    def fetch_metrics(self, fetch_starting_datetime: datetime | None):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.fetch_workload, start_time=fetch_starting_datetime): 'rps',
                executor.submit(self.fetch_node_cpu_usage): 'node_cpu',
                executor.submit(self.fetch_pod_cpu_usage): 'pod_cpu',
                executor.submit(self.fetch_ready_pod_count): 'ready_pod',
                executor.submit(self.fetch_pod_count): 'pod'
            }

            results = {}
            for future in concurrent.futures.as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    print(f"An error occurred fetching {key}: {e}")
                    results[key] = None

        return results

    def fetch_pod_cpu_usage(self):
        query = \
            """
            sum by (group) (
                label_replace(
                    rate(container_cpu_usage_seconds_total{
                        namespace="default", 
                        pod=~"^s[0-6].*"
                    }[1m]), 
                    "group", 
                    "$1", 
                    "pod", 
                    "^([a-z0-9]+)-[a-z0-9]+-[a-z0-9]+$"
                )
            ) 
            / 
            count by (group) (
                label_replace(
                    kube_pod_status_ready{
                        namespace="default", 
                        condition="true", 
                        pod=~"^s[0-6].*"
                    },
                    "group",
                    "$1",
                    "pod",
                    "^([a-z0-9]+)-[a-z0-9]+-[a-z0-9]+$"
                )
            ) * 100 * 0.05
            """
        response = self.prometheus.custom_query(query=query)
        return {item['metric']['group']: float(item['value'][1]) for item in response}

    def fetch_node_cpu_usage(self):
        query = \
            """
            (100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)) / 100
            """
        response = self.prometheus.custom_query(query=query)
        return {'cpu_node': float(response[0]['value'][1])}

    def fetch_ready_pod_count(self):
        query = \
            """
            count by(group) (
                label_replace(
                    kube_pod_status_ready{
                        namespace="default", 
                        condition="true", 
                        pod=~"^s[0-6].*"
                    },
                    "group",
                    "$1",
                    "pod",
                    "^([a-z0-9]+)-[a-z0-9]+-[a-z0-9]+$"
                )
            )
            """
        response = self.prometheus.custom_query(query=query)
        return {item['metric']['group']: int(item['value'][1]) for item in response}

    def fetch_pod_count(self):
        query = \
            """
            count by (group) (
                label_replace(
                    kube_pod_info{
                        namespace="default",
                        pod=~"^s[0-6].*"
                    }, 
                    "group", 
                    "$1", 
                    "pod", 
                    "^([a-z0-9]+)-[a-z0-9]+-[a-z0-9]+$"
                )
            )
            """
        response = self.prometheus.custom_query(query=query)
        return {item['metric']['group']: int(item['value'][1]) for item in response}

    def fetch_workload(
        self,
        start_time=parse_datetime("now-24h"),
        end_time=parse_datetime("now"),
        step="60s",
    ):
        query = \
            """
            sum by (app_name) (
                rate(
                    mub_internal_processing_latency_milliseconds_count{
                        namespace="default",
                        pod=~"^s[0-6].*"
                    }[1m]
                )
            )
            """
        response = self.prometheus.custom_query_range(
            query=query,
            start_time=start_time,
            end_time=end_time,
            step=step,
        )

        return {item['metric']['app_name']: [float(value[1]) for value in item['values']] for item in response}
