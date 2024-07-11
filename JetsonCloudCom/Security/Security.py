from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding,rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

def Sign_Encrypt(Data):
    with open("./Security/keys/private_sign.pem", "rb") as key_file:
        sign_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )

    with open("./Security/keys/public_data.pem","rb") as data_key:
        enc_key = serialization.load_pem_public_key(
            data_key.read()
        )
        
    
    # print(type(message.encode('utf-8')))

    signature = sign_key.sign(
        # Data.encode('utf-8'),
        Data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    key = os.urandom(32)
    # Generate a random 96-bit nonce
    nonce = os.urandom(12)  # 96 bits = 12 bytes

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()

    transfer_data = Data + signature

    # Encrypt the data
    ciphertext = encryptor.update(transfer_data) + encryptor.finalize()
    tag = encryptor.tag

    print(len(nonce))

    aes_key = key + nonce + tag

    aes_key_enc = enc_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return aes_key_enc + ciphertext

def Verify_Decrypt(Enc_data):
    with open("./Security/keys/public_sign.pem", "rb") as key_file:
        verify_key = serialization.load_pem_public_key(
            key_file.read()
        )

    with open("./Security/keys/private_data.pem","rb") as data_key:
        dec_key = serialization.load_pem_private_key(
            data_key.read(),
            password=None
        )


    aes_key_enc = Enc_data[:256]

    aes_key = dec_key.decrypt(
        aes_key_enc,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )


    enc_signed_data = Enc_data[256:]

    key = aes_key[:32]
    nonce = aes_key[32:44]
    tag = aes_key[44:]

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
    decryptor = cipher.decryptor()

    # Decrypt the data
    decrypted_data = decryptor.update(enc_signed_data) + decryptor.finalize()

    message = decrypted_data[:-256]  # Assuming signature is last 256 bytes
    signature = decrypted_data[-256:]

    try:
        verify_key.verify(
            signature,
            message,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print("Signature verified!")
        # print("Decrypted message:", message.decode('utf-8'))
        # Dec_data = message
        return message
    except Exception as e:
        print("Signature verification failed:", e)
        return None

