import requests 
  
API_ENDPOINT = "http://127.0.0.1:8080"

params = {
    "hello": "world"
}  
print("Sending get request to Fusion 360...")
response = requests.get(url=API_ENDPOINT, params=params) 
print("Get Response", response)

data = {
    "hello": "world"
} 
print("Sending post request to Fusion 360...")
response = requests.post(url=API_ENDPOINT, data=data) 
print("Post Response", response)