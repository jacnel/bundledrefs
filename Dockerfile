# This Dockerfile configures the environment necessary to run our code. It takes care
# of installing the necessary utilities and libraries. This includes downloading and
# installing conda, setting up the conda environment, and creating a symbolic link
# for the jemalloc libraries.

FROM ubuntu:focal
ENV TERM xterm-256color

# Install necessary utilities.
RUN apt-get upgrade && apt-get update
RUN apt-get install -y wget openssh-server make sudo g++ libnuma-dev libpapi-dev vim dos2unix bc

# Download and install Miniconda under `/opt/conda` with the group `conda`. Then, do some
# cleanup and add the conda binaries to PATH. Note that it is possible that the checksum
# is not up to date since we install the latest version of Miniconda. If you are having
# trouble with the checksum failing, go to https://docs.conda.io/en/latest/miniconda.html
# and ensure that the below value is correct.
ARG INSTALLER=Miniconda3-latest-Linux-x86_64.sh
ARG SHA256SUM=1ea2f885b4dbc3098662845560bc64271eb17085387a70c2ba3f29fff6f8d52f

RUN groupadd conda
RUN mkdir -p /opt
RUN cd /tmp && wget https://repo.anaconda.com/miniconda/${INSTALLER} && \
	echo "${SHA256SUM} ${INSTALLER}" | sha256sum --check && \
	chmod +x ${INSTALLER} && \
	./${INSTALLER} -b -p /opt/conda
RUN chgrp -R conda /opt/conda && chmod -R g+w /opt/conda
RUN rm /tmp/${INSTALLER}
RUN ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh
RUN echo ". /opt/conda/etc/profile.d/conda.sh" >>~/.bashrc && echo "conda activate base" >>~/.bashrc
RUN find /opt/conda/ -follow -type f -name '*.a' -delete && \
	find /opt/conda/ -follow -type f -name '*.js.map' -delete && \
	/opt/conda/bin/conda clean -afy
ENV PATH /opt/conda/bin:$PATH

# Configure a user that will be used to run the project.
RUN useradd -ms /bin/bash -G conda,sudo bundledrefs
RUN echo 'bundledrefs:bundledrefs' | chpasswd

# Add the current directory to the new user's home directory, set up 
# the conda environment, and link in jemalloc. Make sure the environment 
# is activated automatically whenever the user logs in.
ARG PROJECT_DIR=bundledrefs

USER bundledrefs
RUN conda create -y -n bundledrefs python=3 plotly psutil requests pandas absl-py
RUN conda install -n bundledrefs -c conda-forge jemalloc
RUN echo "conda activate bundledrefs" >>/home/bundledrefs/.bashrc

ADD --chown=bundledrefs:bundledrefs . /home/bundledrefs/${PROJECT_DIR}
RUN rm -f /home/bundledrefs/${PROJECT_DIR}/lib/*
RUN mkdir -p /home/bundledrefs/${PROJECT_DIR}/lib && \
	ln -s /opt/conda/envs/bundledrefs/lib/libjemalloc.so /home/bundledrefs/${PROJECT_DIR}/lib/libjemalloc.so

# This image exposes a port that hosts an ssh server for users to connect to.
# The container port will be 22, but it must be mapped to host port when running
# the container. If you are using the command line interface, this can be
# accomplished by running the image with the command `docker run -p 8022:22 <image_name>`.
# Then, ssh-ing into the container using `ssh -p 8022 bundledrefs@localhost` and the 
# password `bundledrefs`.
USER root
EXPOSE 22
RUN service ssh start
CMD ["/usr/sbin/sshd", "-D"]
