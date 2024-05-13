from prometheus_api_client import PrometheusConnect
from prometheus_api_client.utils import parse_datetime

from prometheus.config import PROMETHEUS_URL


class PrometheusClient(object):
    prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)

    @staticmethod
    def fetch_cpu_usage():
        query = \
            """
            (
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
            ) * 100 * 0.05
            """
        response = PrometheusClient.prom.custom_query(query=query)
        return {item['metric']['group']: float(item['value'][1]) for item in response}

    @staticmethod
    def fetch_pod_count():
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
        response = PrometheusClient.prom.custom_query(query=query)
        return {item['metric']['group']: int(item['value'][1]) for item in response}

    def fetch_workload(
        start_time=parse_datetime("2024-05-13 03:05:00"),
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
        response = PrometheusClient.prom.custom_query_range(
            query=query,
            start_time=start_time,
            end_time=end_time,
            step=step,
        )

        return {item['metric']['app_name']: [float(value[1]) for value in item['values']] for item in response}
