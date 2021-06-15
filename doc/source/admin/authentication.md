# Authentication

Galaxy supports the following authentication mechanisms:

* [Galaxy Database](#galaxy-database) - Galaxy-specific login using e-mail address and password (the default);
* [OIDC and OAuth2.0](#OIDC-and-OAuth2.0) - Login to Galaxy using your Google account, without having to create a Galaxy user;
* [Authentication Framework](#authentication-framework) - A plugin-driven framework supporting LDAP/Active Directory and PAM;
* [Proxy Authentication](#proxy_authentication) - HTTP [remote user](http://httpd.apache.org/docs/current/mod/mod_cgi.html#env) provided by any front-end Web server.

## Galaxy Database

Without any additional configuration Galaxy will simply use its database to maintain usernames and passwords. The
Galaxy user interface and API provide functions allowing users to register accounts, change passwords, etc....

If deploying Galaxy using the default authentication option, user activation can be enabled also. This is documented
[below](#user-activation).

## OIDC and OAuth2.0
Leveraging OpenID Connect (OIDC) protocol, we enable login to Galaxy without explicitly creating a Galaxy user. This feature is disabled by default. In short, to enable this feature, a Galaxy server admin has to take the following two steps: 

1. Define the Galaxy instance on an OIDC identity provider. At the moment, we support Google and Okta. To set a Galaxy instance on Google, go to _credentials_ section at [developers console](https://console.developers.google.com/), and configure the instance. At the end, you'll receive _client ID_ and _client secret_ take a note of these two tokens. For Okta, create a new application in Okta, type _web_. At the end you should take note of the _client ID_ and _client secret_ tokens.

2. Configure Galaxy. In the `galaxy.yml` file enable the OIDC service using the `enable_oidc` key and set the two configuration files (i.e., `oidc_config_file` and `oidc_backends_config_file`), based on the IdP information. 

The configuration is explained with provider-specific details at [User Authentication Configuration](https://galaxyproject.org/authnz/config/oidc/). How to authenticate from the user perspective we describe [here](https://galaxyproject.org/authnz/use/oidc/).

## Authentication Framework

Galaxy is distributed with a plugin-driven authentication framework for which the default database authentication is
just one (and the default plugin). This framework can be used to allow Galaxy to delegate authentication to
an LDAP server, an Active Directory server, or to PAM.

These same mechanisms can also be configured by proxies serving Galaxy (e.g. nginx or Apache), but configuring them
within Galaxy allows users to use the Galaxy UI for logging in instead of relying on a proxy.

To configure one or more authentication plugins, simply copy ``config/auth_conf.xml.sample`` to ``config/auth_conf.xml``.
The provided sample configuration file has numerous commented out examples and serves as the most up-to-date source
of documentation on configuring these plugins.

## Remote User Authentication

If Galaxy is deployed with either nginx or Apache serving as a front-end proxy for Galaxy requests, they can be configured
to authenticate users and pass this authentication information along to Galaxy using the HTTP remote user mechanism. See, for
example, the [authentication and authorization guide for the Apache Web server](http://httpd.apache.org/docs/2.4/howto/auth.html)
for an impression of the possibilities. Thus, by the time Galaxy is aware of a request, the user identity will have been determined
and there will be no need for Galaxy to do any additional authentication work, such as showing a login screen or checking user
credentials.

However, accepting an identity asserted by the Web server does not relieve Galaxy from having to create a user account for
such an identity. Thus, Galaxy automatically creates a user for each identity of this kind, recording that the user is
"external" and also creating a random password in order to effectively disable traditionally performed logins for the user,
although the remote user mechanism should normally prohibit any login mechanism other than that imposed by the Web server,
and the "external" flag should itself prohibit the traditional mechanism being used with the user concerned. When a remote
user returns to Galaxy and is not already logged in, the details of the user are retrieved according to the identity
information supplied by the Web server.

Enabling remote user authentication requires you to edit Galaxy's configuration file and set `use_remote_user` to `true`.
This file is likely located in `config/galaxy.yml` and can be created by copying Galaxy's sample `config/galaxy.yml.sample`.

Additional Galaxy configuration options related to remote user authentication are documented in Galaxy's sample 
configuration file. The options ``remote_user_maildomain``, ``remote_user_header``, and ``normalize_remote_user_email`` can
adapt Galaxy to different responses from the proxy, while ``remote_user_secret`` can be used to provide added
security, and ``remote_user_logout_href`` can be used to fix Galaxy's logout for the deployed setup.

## User Activation

Galaxy admins using the default authentication mechanism have an option to turn on the email verification feature
to force users to provide working email during the registration. You can also turn on the disposable email domains
filter to disable registration for users using known disposable email provider. 

How to set up this config is presented here.

*Note: SQLite database is not supported with this feature. Please use PostgreSQL.*

### Account activation feature

In the Galaxy config file **config/galaxy.yml** there is the user activation setting that you have to turn on.

```yaml
user_activation_on: true
```


There is also the option for tracking jobs in database that is required to be turned on for the account activation to be effective. By default it is off.

```yaml
track_jobs_in_database: true
```


After you turn on both of these every user that will try to register after this configuration file takes effect will have the verification email sent to the email address provided. Unless the Grace period (see below) is set, the user won't be able to login before the verification happens.

Furthermore in order for this to work correctly smtp server and admin email should be set:

```yaml
smtp_server: some.server.edu:587
smtp_username: example_username
smtp_password: example_passsword
activation_email: activation-noreply@example.com
error_email_to: admin@example.com
```

Smtp server takes care of the email sending and the activation_email email is used as the *From* address in the verification email. Furthermore the error_email_to is being shown to the user if the Galaxy detects its own misconfiguration.

You can also set the instance_resource_url which is shown in the activation emails so you can point users to your wiki or other materials.
```
instance_resource_url = http://galaxyproject.org/
```


The final activation email looks like this:

```
Hello <user_name>,

In order to complete the activation process for <user_email> begun on <date> at <hostname>, please click on the following link to verify your account:

test.galaxyproject.org/activate?activation_token=46701ecdbbf2a79a7348ddae33062774edadef59&email=example%40example.com

By clicking on the above link and opening a Galaxy account you are also confirming that you have read and agreed to Galaxy's Terms and Conditions for use of this service (<link_to_terms_config>). This includes a quota limit of one account per user. Attempts to subvert this limit by creating multiple accounts or through any other method may result in termination of all associated accounts and data.

Please contact us if you need help with your account at: <error_email_to_config>. You can also browse resources available at: <instance_resources_url_config>.

More about the Galaxy Project can be found at galaxyproject.org

Your Galaxy Team

```

### Changing email address

If an activated user changes email address in user settings, his/her account will be deactivated. A new activation link will be sent and the user will have to visit it to activate the account again.

### Grace period

In case you want the account activation feature but don't want to disable login completely you can set the **activation_grace_period** parameter. It specifies, in hours, the period in between registration time and the login time that the user will be allowed to log in even with an inactive account. 
```
# Activation grace period. Activation is not forced (login is not disabled) until 
# grace period has passed. Users under grace period can't run jobs (see inactivity_box_content).
# In hours. Default is 3. Enter 0 to disable grace period. 
# Users with OpenID logins have grace period forever. 
#activation_grace_period = 3
```

However with inactive account the user won't be able to run jobs and warning message will be shown to him at the top of the page. It is customizable via the **inactivity_box_content** parameter.
```
# Used for warning box for inactive accounts (unable to run jobs).
# In use only if activation_grace_period is set.
#inactivity_box_content = Your account has not been activated yet. Please activate your account by verifying your email address. For now you can access everything at Galaxy but your jobs won't run.
```

### Disposable email address filtering

<a name="disposable_email_filter"></a>

To prevent users from using disposable email addresses as a workaround for the email verification the domain blacklist can be turned on through the **blacklist_file** path parameter. Users that use disposable email domains defined at the file in this provided path will be refused registration.
```
# E-mail domains blacklist is used for filtering out users that are using disposable email address
# during the registration. If their address domain matches any domain in the BL they are refused the registration.
blacklist_file = config/disposable_email_blacklist.conf
```


Disposable domains blacklist file for download and modification is [at GitHub](https://github.com/martenson/disposable-email-domains/blob/master/disposable_email_blacklist.conf)

In the file each domain is on its own line and without the *@* sign. Example of the blacklist file format:

```
drdrb.com
mailinator.com
sogetthis.com
spamgourmet.com
trashmail.net
kurzepost.de
objectmail.com
proxymail.eu
rcpt.at
trash-mail.at
trashmail.at
trashmail.me
wegwerfmail.de
wegwerfmail.net
wegwerfmail.org
```

## Authentication Related Code

The `lib/galaxy/webapps/galaxy/controllers/user.py` file provides much of the authentication-related logic in the `User` class. Of the supported mechanisms, only those needing to perform actual authentication work require any substantial amount of code in this file; the integration of "remote user" information is performed in the `lib/galaxy/web/framework/__init__.py` file.

Within the `User` class, code supporting authentication mechanisms will need to provide the following things:

* Support within the `login` method for any additional information shown in the login screen. Since the login screen is likely to be modified to show alternative authentication methods alongside the conventional e-mail and password fields, it is possible that information such as identity providers will also need to be made available in order to simplify the experience for users.
* A separate method to handle the initial stage of authentication for the mechanism. For example, OpenID authentication requests are handled by the `openid_auth` method initially.
* Additional methods to handle any subsequent stages of authentication. For example, OpenID authentication involves the handling of subsequent requests in the `openid_process`, `openid_associate` and `openid_manage` methods.

### Database Tables

The database employs a `galaxy_user` table which records the details of all registered users, and this table is exposed to the code through the `User` abstraction found in `lib/galaxy/model/mapping.py`. Each logged-in user is assigned a session which references the user in the `galaxy_session` table (exposed via `GalaxySession`).

User information from external sources, such as OpenID, is found in peripheral tables such as `galaxy_user_openid` (exposed by `UserOpenID`) and references the registered user and session of that user.

### Authenticating a User

The following steps are followed in any code that seeks to recognise a user within Galaxy and allow access to the application:

1. The identity credential, currently the e-mail address of the user, is used to find any previously-registered user in the database.
1. Where no user exists and the login mechanism requires explicit registration, authentication fails at this point. Otherwise, a user is automatically created for previously unknown identities.
1. For conventional accounts requiring a password, authentication fails at this point if a valid password is not specified. Otherwise, an alternative mechanism for completing authentication may be invoked.
1. Upon completion of the authentication of a user's identity, any association of that identity with the Galaxy user instance may be performed. For example, an OpenID identity may be associated with a user created for that identity.
1. Finally, the login is handled using the `handle_user_login` method on the `GalaxyWebTransaction` object, associating the user with a new session.
