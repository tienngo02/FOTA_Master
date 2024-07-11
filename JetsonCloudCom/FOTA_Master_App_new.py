from Crypto.PublicKey import RSA

secret_code = "Unguessable"
key = RSA.generate(16384)

with open("rsa_private_key.bin", "wb") as f:
    f.write(key)

encrypted_key = key.export_key(passphrase=secret_code, pkcs=8,
                              protection="scryptAndAES128-CBC",
                              prot_params={'iteration_count':131072})

with open("rsa_key.bin", "wb") as f:
    f.write(encrypted_key)


print(key.publickey().export_key())