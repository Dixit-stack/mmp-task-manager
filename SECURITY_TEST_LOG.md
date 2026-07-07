# Security Test Log - ishwor karki

## Test 1: SQL Injection on Login
Payload tested: x@x.com' OR '1'='1
Method: curl POST request to /login endpoint
Result: Rejected - server returned "Invalid email or password", confirming the parameterised query (WHERE u.email = ?) prevents the injection payload from executing as SQL.

## Test 2: Password Storage Verification
Verified via direct database query (SELECT * FROM users in sqlite3) that the password_hash column contains a salted hash generated using scrypt, not a plaintext password.

## Conclusion
Both core security controls (SQL injection prevention via parameterised queries, and password hashing) were independently tested and confirmed working as implemented.
