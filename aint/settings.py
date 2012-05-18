"""Sample settings file."""

# Domain name suffix for all DNS entries.
dns_suffix = "atunit.org"

# Path to the ssh privante key. Can be relative, and can have ~ in it
# for $HOME
ssh_key_path = "~/.ssh/atunit.pem"

# /etc repository information
etc_repo_uri = "git@memrise.unfuddle.com:memrise/etc.git"
etc_repo_email = "info@memrise.com"
etc_repo_user = "Atunit root"

# Name of apache configuration to use after checking out the /etc
# configuration.
site_config_name = "memrise"

