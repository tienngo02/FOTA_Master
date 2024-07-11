from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

#message = "I want this stream signed"
with open("main.py","r") as input:
    message = input.read()
# message = input("message? ")
digest = SHA256.new()
digest.update(message.encode('utf-8'))

# Load private key previouly generated
with open ("private_key.pem", "r") as myfile:
    sign_key = RSA.importKey(myfile.read())
with open("private_data.pem","r") as data_key:
    enc_key = RSA.importKey(data_key.read())

# Sign the message
signer = PKCS1_v1_5.new(sign_key)
sig = signer.sign(digest)

cipher_rsa = PKCS1_OAEP.new(enc_key)

# sig is bytes object, so convert to hex string.
# (could convert using b64encode or any number of ways)
print("Signature:")
print(sig.hex())


enc_message = cipher_rsa.encrypt(message)

encrypted_data = enc_message.encode('utf-8') + sig
print("Length: ",len(sig))

# message_json = json.dumps({
#     'data': message.decode('u')
# })

with open('signed_data.txt','w') as data_file:
    data_file.write(encrypted_data.hex())