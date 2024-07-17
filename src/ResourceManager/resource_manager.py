import logging
from kubernetes import client, config

logger = logging.getLogger("ResourceManager")


class ResourceManager:
    def __init__(self):
        config.load_incluster_config()
        self.v1 = client.AppsV1Api()

    def scale_deployment(
        self,
        deployment_name: str,
        replicas: int,
        namespace: str = 'default'
    ):
        logger.info(f"Scaling {deployment_name} to {replicas} replica(s).")
        patch_body = {
            "spec": {
                "replicas": replicas
            }
        }
        return self.v1.patch_namespaced_deployment_scale(
            name=deployment_name,
            namespace=namespace,
            body=patch_body
        )

    def get_deployment_info(
        self,
        deployment_name: str,
        namespace: str = 'default'
    ):
        return self.v1.read_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
        )
