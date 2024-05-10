from prometheus.client import PrometheusClient
from k8s.client import K8sClient

if __name__ == '__main__':
    print(K8sClient.get_deployment_info(deployment_name='s0'))