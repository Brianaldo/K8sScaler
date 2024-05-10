from kubernetes import client, config

class K8sClient(object):
    config.load_incluster_config()
    v1 = client.AppsV1Api()

    @staticmethod
    def scale_deployment(
        deployment_name: str, 
        replicas: int, 
        namespace: str = 'default'
    ):
        patch_body = {
            "spec": {
                "replicas": replicas
                }
            }
        return K8sClient.v1.patch_namespaced_deployment_scale(
            name=deployment_name, 
            namespace=namespace, 
            body=patch_body
        )
    
    @staticmethod
    def get_deployment_info(
        deployment_name: str, 
        namespace: str = 'default'
    ):
        return K8sClient.v1.read_namespaced_deployment(
            name=deployment_name, 
            namespace=namespace,
        )