import asyncio
import websockets
import json


async def send_json(uri, data, headers):
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        json_data = json.dumps(data)
        await websocket.send(json_data)
        response = await websocket.recv()

        response = json.loads(response)
        while response["finish_reason"] is None:
            response = await websocket.recv()
            response = json.loads(response)
            print(response)


if __name__ == "__main__":
    uri = "uri"
    headers = [("X-API-Key", "<KEY>")]
    data = {
        "query": "Co sie znajduje w tym dokumencie oraz ile mam lat?",
        "context": "--- Document file1.txt ---\n\nChunk 0\n\nhahaha\n\n--- Document file2.txt ---\n\nChunk 0\n\nhahaha\n\n",
        "conversation":
            [
                {"type": "system", "content": "Witaj!"},
                {"type": "user", "content": "Mam 44 lata."},
            ]
    }

    asyncio.get_event_loop().run_until_complete(send_json(uri, data, headers))

