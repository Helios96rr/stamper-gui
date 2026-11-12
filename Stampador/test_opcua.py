
import asyncio
from asyncua import Client

# Dirección del servidor OPC UA del PLC
ENDPOINT = "opc.tcp://172.16.1.95:4840"

async def main():

    try:
        async with Client(url=ENDPOINT) as client:

            print("Conexión OPC UA establecida")

            # Obtener información del servidor
            namespaces = await client.get_namespace_array()

            print("\nNamespaces disponibles:")

            for index, namespace in enumerate(namespaces):
                print(f"Namespace {index}: {namespace}")

            # Explorar los objetos del servidor
            objects = client.nodes.objects

            children = await objects.get_children()

            print("\nObjetos disponibles:")

            for node in children:
                print(
                    node,
                    await node.read_browse_name()
                )

    except Exception as error:
        print("Error de comunicación OPC UA:")
        print(error)


if __name__ == "__main__":
    asyncio.run(main())
