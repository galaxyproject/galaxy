# Galaxy FTP Uploads

To allow users to upload files to Galaxy via FTP, you'll need to configure Galaxy and install an FTP server. After everything is configured users will be able to upload their files through the FTP server and then select them for importing in the upload dialog in Galaxy.

For help with uploading data via FTP on Galaxy [Main](https://galaxyproject.org/main/), please see this [tutorial](https://galaxyproject.org/ftp-upload/).

## Install some FTP server

Although there is no specific required server, we use [ProFTPD](http://proftpd.org/) for our [public site](http://usegalaxy.org/) since it supports all the things we'll need to be able to do, such as authenticating against the Galaxy database. We recommend you to use the same FTP server as the configurations we provide are targeting it. You can also browse the list of alternative FTP servers at http://en.wikipedia.org/wiki/List_of_FTP_server_software

## Configure Galaxy

The first step is to choose a directory into which your users will upload files.  Preferably this will be on the same filesystem as Galaxy's datasets (by default, `galaxy_dist/database/files/`).  The FTP server will create subdirectories inside of this directory which match the user's email address.  Likewise, Galaxy will expect to find email-named subdirectories at that path.  This directory should be set in the config file (`galaxy.yml`) as `ftp_upload_dir`.

In the config file, you'll also want to set `ftp_upload_site` to the hostname your users should connect to via FTP.  This will be provided in the help text on the Upload File form.

## Allow your FTP server to read Galaxy's database

You'll need to grant a user access to read emails and passwords from the Galaxy database.  Although the user Galaxy connects with could be used, I prefer to use a least-privilege setup wherein a separate user is created for the FTP server which has permission to `SELECT` from the `galaxy_user` table and nothing else.  In postgres this is accomplished with:

```bash
postgres@dbserver% createuser -SDR galaxyftp
postgres@dbserver% psql galaxydb
Welcome to psql 8.X.Y, the PostgreSQL interactive terminal.

Type:  \copyright for distribution terms
       \h for help with SQL commands
       \? for help with psql commands
       \g or terminate with semicolon to execute query
       \q to quit

galaxydb=# ALTER ROLE galaxyftp PASSWORD 'dbpassword';
ALTER ROLE
galaxydb=# GRANT SELECT ON galaxy_user TO galaxyftp; 
GRANT
```


## Configuring ProFTPD

By default, Galaxy stores passwords using [PBKDF2](http://en.wikipedia.org/wiki/PBKDF2). It's possible to disable this using the `use_pbkdf2: false` setting in the `galaxy` section of `galaxy.yml`. Once disabled, any new passwords created will be stored in an older hex-encoded SHA1 format. Because of this, it's possible to have both PBKDF2 and SHA1 passwords in your database (especially if your server has been around since before PBKDF2 support was added). Although this is fine (Galaxy can read passwords in either format), ProFTPD will expect them in one format or the other (although with some amount of hackery it could probably be made to read both).

Because of this, you'll need to choose one or the other in your Galaxy config (PBKDF2 is more secure and therefore preferred) and configure ProFTPD accordingly. If users cannot log in because their password is stored in the wrong format, they can simply use Galaxy's password change form to set their password, which will rewrite their password using the currently configured algorithm.

For more hints on the PBKDF2 configuration, see the fantastic blog post [FTP upload to Galaxy using ProFTPd and PBKDF2](http://galacticengineer.blogspot.co.uk/2015/02/ftp-upload-to-galaxy-using-proftpd-and.html) by Peter Briggs (which was used to create the documentation below).

Although any FTP server should work, our public site uses ProFTPD.  You'll need the following extra modules for ProFTPD:

* mod_sql
* mod_sql_postgres or mod_sql_mysql
* mod_sql_passwd

We compile by hand using the following configure arguments (OpenSSL is prebuilt and statically linked), you should read the INSTALL file that come with the proftpd source distribution. At least you should consider if you need to use any of these options "install_user=<user> install_group=<group> ./configure --sysconfdir=/etc --localstatedir=/var":

```console
./configure --prefix=/foo --disable-auth-file --disable-ncurses --disable-ident --disable-shadow --enable-openssl --with-modules=mod_sql:mod_sql_postgres:mod_sql_passwd --with-includes=/usr/postgres/9.1-pgdg/include:`pwd`/../openssl/.openssl/include --with-libraries=/usr/postgres/9.1-pgdg/lib/64:`pwd`/../openssl/.openssl/lib
```


An example configuration follows, assuming `ftp_upload_dir = /home/nate/galaxy_dist/database/ftp` in the Galaxy config file:

```apache

# Basics, some site-specific
ServerName                      "Public Galaxy FTP"
ServerType                      standalone
DefaultServer                   on
Port                            21
Umask                           077
SyslogFacility                  DAEMON
SyslogLevel                     debug
MaxInstances                    30

# This User & Group should be set to the actual user and group name which matche the UID & GID you will specify later in the SQLNamedQuery.
User                            nobody
Group                           nogroup
DisplayConnect                  /etc/opt/local/proftpd_welcome.txt

# Passive port range for the firewall
PassivePorts                    30000 40000

# Cause every FTP user to be "jailed" (chrooted) into their home directory
DefaultRoot                     ~

# Automatically create home directory if it doesn't exist
CreateHome                      on dirmode 700

# Allow users to overwrite their files
AllowOverwrite                  on

# Allow users to resume interrupted uploads
AllowStoreRestart               on

# Bar use of SITE CHMOD
<Limit SITE_CHMOD>
    DenyAll
</Limit>

# Bar use of RETR (download) since this is not a public file drop
<Limit RETR>
    DenyAll
</Limit>

# Do not authenticate against real (system) users
<IfModule mod_auth_pam.c>
AuthPAM                         off
</IfModule>

# Common SQL authentication options
SQLEngine                       on
SQLPasswordEngine               on
SQLBackend                      postgres
SQLConnectInfo                  galaxydb@dbserver.example.org[:port] <dbuser> <dbpassword>
SQLAuthenticate                 users
```


For PBKDF2 passwords, the following additions to `proftpd.conf` should work:

```apache
# Configuration that handles PBKDF2 encryption
# Set up mod_sql to authenticate against the Galaxy database
SQLAuthTypes                    PBKDF2
SQLPasswordPBKDF2               SHA256 10000 24 
SQLPasswordEncoding             base64
 
# For PBKDF2 authentication
# See http://dev.list.galaxyproject.org/ProFTPD-integration-with-Galaxy-td4660295.html
SQLPasswordUserSalt             sql:/GetUserSalt
 
# Define a custom query for lookup that returns a passwd-like entry. Replace 512s with the UID and GID of the user running the Galaxy server
SQLUserInfo                     custom:/LookupGalaxyUser
SQLNamedQuery                   LookupGalaxyUser SELECT "email, (CASE WHEN substring(password from 1 for 6) = 'PBKDF2' THEN substring(password from 38 for 69) ELSE password END) AS password2,512,512,'/home/nate/galaxy_dist/database/ftp/%U','/bin/bash' FROM galaxy_user WHERE email='%U'"
 
# Define custom query to fetch the password salt
SQLNamedQuery                   GetUserSalt SELECT "(CASE WHEN SUBSTRING (password from 1 for 6) = 'PBKDF2' THEN SUBSTRING (password from 21 for 16) END) AS salt FROM galaxy_user WHERE email='%U'"
```

For SHA1 passwords, the following additions to `proftpd.conf` should work:

```apache
# Set up mod_sql/mod_sql_password - Galaxy passwords are stored as hex-encoded SHA1
SQLAuthTypes                    SHA1
SQLPasswordEncoding             hex

# An empty directory in case chroot fails
SQLDefaultHomedir               /var/opt/local/proftpd

# Define a custom query for lookup that returns a passwd-like entry. Replace 512s with the UID and GID of the user running the Galaxy server
SQLUserInfo                     custom:/LookupGalaxyUser
SQLNamedQuery                   LookupGalaxyUser SELECT "email,password,512,512,'/home/nate/galaxy_dist/database/ftp/%U','/bin/bash' FROM galaxy_user WHERE email='%U'"
```


## Further security measures

FTP protocol is **not** encrypted by default, thus any usernames and passwords are sent over clear text to Galaxy. You may wish to implement further security measures by forcing the FTP connection to use SSL/TLS or to allow users to send their files using SFTP (a completely different protocol than FTP - see http://www.proftpd.org/docs/contrib/mod_sftp.html). Here are some extra steps that you can use with ProFTPD.

```apache
<IfModule mod_sftp.c>
  # You must put this in a virtual host if you want it to listen on its own port. VHost != Apache Vhost.
  <VirtualHost IP_of_Galaxy> 
    # You may wish to open a new port for this so that you don't lock yourself out of SSH. I chose 2222
    Port 2222 
    SFTPEngine on
    AuthOrder mod_auth_unix.c mod_sql.c # If you don't do this you will get weird disconnects
    SFTPHostKey /etc/ssh/ssh_host_rsa_key
    # SFTPCiphers aes256-ctr aes192-ctr aes128-ctr # You may wish to lock it to only certain ciphers, 
    # but this is likely to lock out certain users
    RequireValidShell no
    MaxLoginAttempts 6
    ServerName                      "Galaxy SFTP"
    Umask                           077
    User                            galaxyftp
    Group                           galaxyftp
    UseFtpUsers off
    DefaultRoot                     ~
    AllowOverwrite                  on
    AllowStoreRestart               on
    # .. Other rules for directories, etc
    SQLEngine                       on
    SQLGroupInfo                    sftp_groups name id members
    # .. See above, the same SQL rules apply
  </VirtualHost>
</IfModule>
<IfModule mod_tls.c>
    TLSEngine on
    TLSLog /var/log/proftpd/tls.log
    # Make sure that users know that you have to support TLS 1.2! This is very restrictive, but likely the best
    TLSProtocol TLSv1.2
    TLSRSACertificateFile /etc/pki/tls/certs/your_cert.cer
    TLSRSACertificateKeyFile /etc/pki/tls/private/your.key
    TLSCertificateChainFile /etc/pki/tls/certs/your_intermediate.cer
    TLSRenegotiate none
    TLSCipherSuite ALL:!SSLv2:!SSLv3
    TLSVerifyClient off
    TLSRequired auth+data
    TLSOptions NoSessionReuseRequired
    ServerName                      "Galaxy FTP"
    ServerType                      standalone
    DefaultServer                   on
    Port                            21
    Umask                           077
    SyslogFacility                  DAEMON
    SyslogLevel                     debug
    MaxInstances                    30
    User                            galaxyftp
    Group                           galaxyftp
    UseFtpUsers off
    # Passive port range for the firewall - note that you must open these ports for this to work!
    # Since the FTP traffic is now encrypted, your firewall can't peak to see that it is PASSV FTP
    # and it will block it if you don't allow new connections one these ports.
    PassivePorts                    30000 30100
    # Cause every FTP user to be "jailed" (chrooted) into their home directory
    DefaultRoot                     ~
    AllowOverwrite                  on
    # Allow users to resume interrupted uploads
    AllowStoreRestart               on
    # .. Other rules for directories, etc
    SQLEngine                       on
    # .. See above, the same SQL rules apply
</IfModule>
```

You may need to take some additional steps to get this working. Compile ProFTPD --with-modules=mod_sftp:mod_tls as well as sql. You may need to alter your PostGreSQL configuration (typically pg_hba.conf) to allow local IPv6 connections:

```
# IPv6 local connections:
host    all         all         ::1/128               trust
```


You may also need to add a table called 'groups' to allow the SFTP connection to your Galaxy database.

```
psql yourDB
# CREATE TABLE sftp_groups (
    id        char(5) CONSTRAINT firstkey PRIMARY KEY,
    name       varchar(40) NOT NULL,
    members        varchar(100));
```


With these steps, you should be able to allow users to connect to your server using secure protocols.

## Other Links

- [Configuring ProFTP Galaxy Upload for Active Directory](https://galaxyproject.org/admin/config/proftpd-with-ad/)
- [Uploading Data to usegalaxy.org via FTP](https://galaxyproject.org/ftp-upload/)
