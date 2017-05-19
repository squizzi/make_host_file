# Make a Host File
Generate `/etc/hosts` files quickly and easily and scp them to each of the
hosts within an AWS environment.

For the lazy who haven't setup DNS.

## Installation
* Install `python`, `python-pip`, for example on fedora with:

~~~
$ sudo dnf -y install python python-pip
~~~

* Install requirements:
~~~
$ sudo pip install -r requirements.txt
~~~

## Usage
* Provide your AWS SSH identity file for the hosts, along with the environment
file which contains the IP addresses of the hosts to `make_host_file`:
~~~
$ ./make_host_file -i <identity file> -f <env file>
~~~

* Optionally, you can pass a nametype with the `-N` flag to change the name
syntax the hosts will use, instead of 'docker1, docker2, etc.' 'nametype1,
nametype2, etc.'' will be used.
* You can also optionally use the `--make-local` flag to create a local
`/etc/hosts` file which uses the public AWS IPs.

~~~
optional arguments:
  -h, --help            Show help
  -N NAMETYPE           Define a hostname to use to identify hosts in your
                        deployed environment.
  --make-local          Add entries to the hosts in your local /etc/hosts file
                        (requires root) using the public IP's for each host.
  --no-zero             Do not start hostname count from 0, start from 1
                        instead. For example, with --no-zero hosts will be
                        named 'docker1, docker2, etc.' By default host naming
                        will follow the train.env naming convention which is
                        'docker0, docker1, etc.'
required arguments:
  -i SSH_IDENTITY_FILE  Specify the location where your SSH identity file
                        resides for AWS (normally in your train directory).
  -f ENV_FILE           Specify the location/name of the environment.txt file
                        found inside of your train directory. This is used to
                        read IP's of the hosts.
~~~
