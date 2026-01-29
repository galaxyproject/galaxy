# Authentication

Galaxy supports the following authentication mechanisms:

* [Galaxy Database](#galaxy-database) - Galaxy-specific login using e-mail address and password (the default);
* [OIDC and OAuth2.0](#oidc-and-oauth2-0) - Login to Galaxy using your Google account, without having to create a Galaxy user;
* [Authentication Framework](#authentication-framework) - A plugin-driven framework supporting LDAP/Active Directory and PAM;
* [Proxy Authentication](#remote-user-authentication) - HTTP [remote user](http://httpd.apache.org/docs/current/mod/mod_cgi.html#env) provided by any front-end Web server.

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

Currently, we provide two variants of the LDAP authenticator namely, `ldap` and `ldap3`. Both are identical implementations that use different Python modules for binding and making queries to a LDAP server. The authenticator
`ldap` is based on the [python-ldap](https://www.python-ldap.org/) module which is a wrapper around the
OpenLDAP's client library `libldap`. Currently, `python-ldap` does not provide pre-built Python wheel packages and hence, the OpenLDAP client libraries are needed to install `python-ldap` on the Galaxy server.

On the otherhand, `ldap3` is a pure-Python implementation of the OpenLDAP client library and has no external dependencies. This package can be installed out-of-the-box, so we recommend to use it when the OpenLDAP client libraries are not available on the Galaxy server.

These same mechanisms can also be configured by proxies serving Galaxy (e.g. nginx or Apache), but configuring them
within Galaxy allows users to use the Galaxy UI for logging in instead of relying on a proxy.

To configure one or more authentication plugins, simply copy ``config/auth_conf.xml.sample`` to ``config/auth_conf.xml``.
The provided sample configuration file has numerous commented out examples and serves as the most up-to-date source
of documentation on configuring these plugins.

It is relatively straight-forward to add a custom authenticator to the framework. In this example, we will demonstrate
a new authenticator based on the LDAP authenticator that performs custom checks besides password verification for
authenticating a user on the Galaxy instance. First, we will create an authenticator source file
`lib/galaxy/auth/providers/ldap_custom.py` with the following content:

```
import logging
import ipaddress

from ..providers.ldap_ad import LDAP

log = logging.getLogger(__name__)


class LDAPCustom(LDAP):
    """
    Attempts to authenticate users against an LDAP server.
    """

    plugin_type = "ldap_custom"

    def __init__(self):
        super().__init__()

    def authenticate(self, email, username, password, options, request):
        """
        See abstract method documentation.
        """
        if options.get("continue-on-failure", "False") == "False":
            failure_mode = None  # reject and do not continue
        else:
            failure_mode = False  # reject but continue
        # Check if user's remote IP is declared in whitelisted IPs
        if "white-listed-ips" in options:
            user_remote_ip = request.remote_addr
            # Get all white listed IPs from the config file
            white_listed_ips = options.get("white-listed-ips")
            # Convert them into a list
            white_listed_ips = white_listed_ips.split(' ')
            # Convert user remote IP into IPv4Address object
            user_remote_ip_obj = ipaddress.IPv4Address(user_remote_ip)
            white_listed_ip_objs = [ipaddress.IPv4Network(ip) for ip in white_listed_ip_objs]
            # Make sure white_listed_ip_objs is not empty
            if white_listed_ip_objs:
                # Effectively we are checking if remote ip network subnet
                # is subset of allowed subnets. If at least one subnet matches,
                # we allow user to authenticate
                allowed = any(user_remote_ip_obj in sn for sn in white_listed_ip_objs)
                if not allowed:
                    log.info("LDAP authentication: User remote IP is not listed in whitelisted IPs")
                    return failure_mode, "", ""
        return super().authenticate(email, username, password, options, request)

__all__ = ("LDAPCustom",)

```

In this simple custom LDAP authenticator, we are verifying the remote IP address of the client is declared in the whitelisted
IP addresses. The so-called `white-listed-ips` can be provided within the `auth_config.xml` file. However this can be done in
many ways depending on the deployments like getting white listed IPs from LDAP query or simply reading it from a file on the
file system. This list of IP addresses can be a global whitelist or IP addresses per user. In order to use this authenticator,
we need to declare it in the `auth_config.xml` file as `<type>ldap_custom</type>`.

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
to require users to provide working email during the registration. You can also turn on the disposable email domains
filter to disable registration for users using known disposable email provider.

How to set up this config is presented here.

*Note: SQLite database is not supported with this feature. Please use PostgreSQL.*

### Account activation feature

In the Galaxy config file **config/galaxy.yml** there is the user activation setting that you have to turn on. By default it is off.

```yaml
user_activation_on: true
```


There is also the option for tracking jobs in database that is required to be turned on for the account activation to be effective. By default it is off.

```yaml
track_jobs_in_database: true
```


After you turn on both of these every user that will try to register after this configuration file takes effect will have the activation email sent to the email address provided. Unless the `activation_grace_period` (see below) is set, the user won't be able to login before the activation happens.

Furthermore in order for this to work correctly smtp server and email need be set:

```yaml
smtp_server: some.server.edu:587
smtp_username: example_username
smtp_password: example_passsword
email_from: galaxy-instance@example.com
```

Smtp server takes care of the email sending and the `email_from` is used as the *From* address in the verification email.

### Email template

You can modify the activation email body by modifying the provided templates. You can use them in [html](https://github.com/galaxyproject/galaxy/blob/release_23.0/lib/galaxy/config/templates/mail/activation-email.html) or [txt](https://github.com/galaxyproject/galaxy/blob/release_23.0/lib/galaxy/config/templates/mail/activation-email.txt) depending on your emailing configuration.

The mapping of mentioned templates' variables to config options is as follows:
```
"terms_url": config.terms_url,
"contact_email": config.error_email_to,
"instance_resource_url": config.instance_resource_url,
"custom_message": config.custom_activation_email_message,
```

### Changing email address

If an activated user changes email address in user settings, their account will be deactivated. A new activation link will be sent and the user will have to visit it to activate the account again.

### Grace period

In case you want the account activation feature but don't want to disable login completely you can set the `activation_grace_period` parameter. It specifies, in hours, the period in between registration time and the login time that the user will be allowed to log in even with an inactive account.
```
# Activation grace period. Activation is not forced (login is not disabled) until
# grace period has passed. Users under grace period can't run jobs (see inactivity_box_content).
# In hours. Default is 3. Enter 0 to disable grace period.
# Users with OpenID logins have grace period forever.
#activation_grace_period = 3
```

However with inactive account the user won't be able to run jobs and warning message will be shown to them at the top of the page. It is customizable via the `inactivity_box_content` parameter.
```
# Used for warning box for inactive accounts (unable to run jobs).
# In use only if activation_grace_period is set.
#inactivity_box_content = Your account has not been activated yet. Please activate your account by verifying your email address. For now you can access everything at Galaxy but your jobs won't run.
```

### Disposable email address filtering
To prevent users from using unwanted email addresses for the email activation admins can select from two methods of filtering: domain blocking and allowing.

#### Blocklist

The domain blocklist can be turned on through the `email_domain_blocklist_file` path parameter. Users that use disposable email domains defined at the file in this provided path will be refused registration.
```
# E-mail domains blocklist is used for filtering out users that are using disposable email address
# during the registration. If their address domain matches any domain in the BL they are refused the registration.
email_domain_blocklist_file = config/disposable_email_blocklist.conf
```

In the file each domain is on its own line and without the *@* sign. Example of the blocklist file format:

```
drdrb.com
mailinator.com
sogetthis.com
spamgourmet.com
trashmail.net
```

A disposable domains blocklist file for download and modification is [at GitHub](https://github.com/martenson/disposable-email-domains/blob/master/disposable_email_blocklist.conf)

#### Allowlist

The domain allowlist can be turned on through the `email_domain_allowlist_file` path parameter. The file has the same format as the `email_domain_blocklist_file` above. The difference is that domains _outside_ of the allowlist will not be allowed for account registration.

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
