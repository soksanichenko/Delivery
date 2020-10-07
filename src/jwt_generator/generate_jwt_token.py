# coding=utf-8

from datetime import datetime, timedelta

from jwt import encode, decode

private_key_path = 'jwtRS256.key'
public_key_path = 'jwtRS256.key.pub'
algorithm = 'RS256'

payload = {
    'iss': 'ZelGray',
    'exp': datetime.utcnow() + timedelta(hours=3),
}

with open(private_key_path, 'r') as private_key_file:
    private_key = private_key_file.read()
    jwt_token = encode(
        payload,
        private_key,
        algorithm=algorithm,
    )

with open(public_key_path, 'r') as public_key_file:
    public_key = public_key_file.read()
    decode(
        jwt_token,
        public_key,
        algorithm=algorithm,
        options={
            'require_exp': True,
        }
    )

print(jwt_token.decode('utf-8'))
