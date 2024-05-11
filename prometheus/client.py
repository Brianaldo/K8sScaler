from prometheus_api_client import PrometheusConnect
from prometheus_api_client.utils import parse_datetime
from datetime import timedelta

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
                    }[2m]), 
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
        return PrometheusClient.prom.custom_query(query=query)

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
        return PrometheusClient.prom.custom_query(query=query)

    def fetch_workload(
        start_time=parse_datetime("1d"),
        end_time=parse_datetime("now"),
        chunk_size=timedelta(minutes=2)
    ):
        query = \
            """
            sum by (app_name) (
                rate(
                    mub_internal_processing_latency_milliseconds_count{
                        namespace="default",
                        pod=~"^s[0-6].*"
                    }[2m]
                )
            )
            """
        return PrometheusClient.prom.get_metric_range_data(
            query=query,
            start_time=start_time,
            end_time=end_time,
            chunk_size=chunk_size,
        )
