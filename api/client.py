import requests
from lib.types import Query

IP = "http://129.150.38.199:8000/v1/query/"




t2 = Query(text="The Philippine Health Secretary announces a new [MASK] which helps individuals with reading news", words=["test", "t"])

test = requests.get(url=IP, json=t2.model_dump())



print(test.content)
