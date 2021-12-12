FROM ubuntu:focal
ENV TERM xterm-256color

ARG SHA256SUM=1ea2f885b4dbc3098662845560bc64271eb17085387a70c2ba3f29fff6f8d52f
ARG MINICONDA=Miniconda3-latest-Linux-x86_64.sh
ARG PROJECT_DIR=ppopp22ae-paper63

ENV PATH /opt/conda/bin:$PATH

RUN apt-get upgrade && apt-get update
RUN apt-get install -y wget openssh-server make sudo g++ libnuma-dev libpapi-dev vim dos2unix bc

# Download and install Miniconda under `/opt/conda` with the group `conda`. Then, cleanup do some cleanup.
RUN groupadd conda
RUN mkdir -p /opt
RUN cd /tmp && wget https://repo.anaconda.com/miniconda/${MINICONDA} && \
	echo "${SHA256SUM} ${MINICONDA}" | sha256sum --check && \
	chmod +x ${MINICONDA} && \
	./${MINICONDA} -b -p /opt/conda
RUN chgrp -R conda /opt/conda && chmod -R g+w /opt/conda 
RUN rm /tmp/${MINICONDA}
RUN ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh
RUN echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && echo "conda activate base" >> ~/.bashrc
RUN find /opt/conda/ -follow -type f -name '*.a' -delete && \
	find /opt/conda/ -follow -type f -name '*.js.map' -delete && \
	/opt/conda/bin/conda clean -afy

# Download project.
RUN useradd -ms /bin/bash -G conda,sudo ppopp22ae
RUN echo 'ppopp22ae:ppopp22ae' | chpasswd

USER ppopp22ae
# RUN cd /home/ppopp22ae && wget "https://zenodo.org/record/5733438/files/${PROJECT_DIR}.zip"
# RUN cd /home/ppopp22ae && tar -xf ${PROJECT_DIR}.zip  && rm ${PROJECT_DIR}.zip
ADD . /home/ppopp22ae
RUN rm /home/ppopp22ae/${PROJECT_DIR}/lib/*
RUN conda create -y -n ppopp22ae python=3 plotly psutil requests pandas absl-py
RUN conda install -n ppopp22ae -c conda-forge jemalloc
RUN mkdir -p /home/ppopp22ae/${PROJECT_DIR}/lib && \
	ln -s /opt/conda/envs/ppopp22ae/lib/libjemalloc.so /home/ppopp22ae/${PROJECT_DIR}/lib/libjemalloc.so 

USER root
EXPOSE 22
RUN service ssh start
CMD ["/usr/sbin/sshd", "-D"]