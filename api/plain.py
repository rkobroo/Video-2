import json


async def app(scope, receive, send):
	if scope.get("type") != "http":
		return
	body = json.dumps({"status": "ok", "runtime": "python"}).encode("utf-8")
	headers = [
		[b"content-type", b"application/json; charset=utf-8"],
		[b"content-length", str(len(body)).encode("utf-8")],
	]
	await send({
		"type": "http.response.start",
		"status": 200,
		"headers": headers,
	})
	await send({
		"type": "http.response.body",
		"body": body,
		"more_body": False,
	})

# Vercel expects an ASGI app variable
handler = app

