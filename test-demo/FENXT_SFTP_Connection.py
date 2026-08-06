import paramiko

sftp_server = 's21afnx01sftp.nxt.blackbaud.com'
sftp_port = 22
sftp_user = '7ca020b9c30e8f6b4558'
sftp_pass = 'PASSWORD_HERE'  # Replace with your actual password

try:
    transport = paramiko.Transport((sftp_server, sftp_port))
    transport.connect(username=sftp_user, password=sftp_pass)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print("Connected to SFTP server.")
    # List files in the root directory
    for filename in sftp.listdir('.'):
        print(filename)
    # Download a specific file to Desktop
    sftp.close()
    transport.close()
except Exception as e:
    print("SFTP connection failed:", e)
