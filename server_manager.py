import os
if not os.environ.get('PRODUCTION'):
    from dotenv import load_dotenv
    load_dotenv()
from server import Server

vk_api_token = os.environ['VK_API_TOKEN']
vk_group_id = os.environ['VK_GROUP_ID']

server = Server(vk_api_token, vk_group_id, "info_server")

if __name__ == '__main__':
    server.start()
