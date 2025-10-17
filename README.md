# Bullseye
Embedded systems project for the course PCS3858. Using a raspberry 3B as a controller, the system is capable of identifying and tracking specified people.

TODO: configure dependencies in .toml

## Poetry
Locks the versions of the libraries used, so that all users are more likely to experience the same program behavior and the version conflicts are eliminated. To use Poetry, follow the steps below.

First, install the Poetry library.
```sh
curl -sSL https://install.python-poetry.org | python3 -
```

Inside the projects root folder, apply the command:
```sh
poetry install
```

Now it should be read to go.

### Updating the packages and versions:
First, activate the virtual environment of poetry:
```sh
 poetry env activate
```

Then, add libraries as follows:
```sh
poetry add gpiozero
```

The lock and toml files should update correctly and automatically.