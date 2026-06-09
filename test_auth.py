import sys
sys.path.insert(0, '/Users/swaransh/Desktop/untitled folder 2')

from backend.services.auth_service import (
    get_password_hash, verify_password, 
    create_access_token, verify_access_token
)

h = get_password_hash('mypassword123')
assert verify_password('mypassword123', h), "Password verify failed"
print("Password hash/verify: OK")

tok = create_access_token('user-abc')
print(f"Token type: {type(tok).__name__}, starts with: {tok[:20]}...")

claims = verify_access_token(tok)
print(f"Claims: {claims}")
assert claims is not None, "verify_access_token returned None"
assert claims.get('sub') == 'user-abc', f"Expected sub='user-abc', got {claims.get('sub')}"
print("All auth_service checks: PASSED")
