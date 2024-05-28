FROM ubuntu:24.04

# mara-base section
ARG python_version=3.8

RUN apt-get update -y \
    && apt-get install -y \
                build-essential \
                git \
                dialog \
                coreutils \
                graphviz \
                software-properties-common \
                postgresql-client \
                rsync
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update -y \
    && apt-get install -y \
                python$python_version \
                python$python_version-dev \
                python$python_version-venv \
                python3-venv \
                python-psycopg2 \
                libpq-dev

# ========================================================================================================
# Install go-crond (from https://github.com/webdevops/go-crond)
#
#
# CRON Jobs in OpenShift:
# - https://blog.danman.eu/cron-jobs-in-openshift/
#
# - go-crond was selected over OpenShift cron jobs, and attempting to get crond running on OpenShift
#   - Allows the mara container to be running and the user interface to be available.
#   - The history issues with the OpenShift cron jobs are avoided.
# --------------------------------------------------------------------------------------------------------
ARG SOURCE_REPO=webdevops
ARG GOCROND_VERSION=22.9.1
ADD https://github.com/$SOURCE_REPO/go-crond/releases/download/$GOCROND_VERSION/go-crond.linux.amd64 /usr/bin/go-crond
RUN chmod ug+x /usr/bin/go-crond
# ========================================================================================================

# mara-app section - this is specific to our use of mara
# ======================================================

# Add mara user
ARG uid=1001
ARG user=mara
RUN useradd -U -ms /bin/bash -u $uid $user \
    && usermod -a -G root $user

ENV HOME="/data-pipeline"
ENV PYENV_ROOT=$HOME/.venv
ENV APP_ROOT=$HOME \
    PATH=$PYENV_ROOT/bin:$PATH \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    SHELL=/bin/bash \
    PIP_NO_CACHE_DIR=off \
    PYTHON_VERSION=$python_version \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 

# Copy source code
ADD . $APP_ROOT
ADD ./.scripts $APP_ROOT
ADD ./docker/mara-app/docker-entrypoint.sh $APP_ROOT
ARG entrypoint=$APP_ROOT/docker-entrypoint.sh

WORKDIR $APP_ROOT
RUN make install-packages

# pin previous version of sqlalchemy_utils work avoid bug in 0.36.8
RUN pip install sqlalchemy==1.3.23
RUN pip install sqlalchemy_utils==0.36.7

# Set ownership and permissions
# Set scripts as executable (make files and python files do not have to be marked)
# Make /etc/passwd writable for the root group so an entry can be created for an OpenShift assigned user account.
RUN chown -R mara:root $APP_ROOT \
    && chmod -R ug+rw $APP_ROOT \
    && chmod ug+x $APP_ROOT/scripts/*.sh \
    && chmod ug+x $APP_ROOT/.scripts/mara-app/*.sh \
    && chmod ug+x $APP_ROOT/.scripts/mara-app/makeshell \
    && chmod ug+x $entrypoint \
    && chmod g+rw /etc/passwd \
    && chmod g-w $APP_ROOT/scripts/cron/*

USER $user
ENTRYPOINT ["bash", "docker-entrypoint.sh"]