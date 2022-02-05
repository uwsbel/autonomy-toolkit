ARG ROS_DISTRO

FROM ros:${ROS_DISTRO}

LABEL maintainer="Simulation Based Engineering Laboratory <negrut@wisc.edu>"

ARG PROJECT
ARG ROS_DISTRO
ARG DEBIAN_FRONTEND=noninteractive

# Various arguments and user settings
ARG USERNAME
ARG USERHOME="/home/$USERNAME"
ARG USERSHELL=bash
ARG USERSHELLPATH="/bin/${USERSHELL}"
ARG USERSHELLPROFILE="$USERHOME/.${USERSHELL}rc"

# Check for updates
RUN apt-get update && apt-get upgrade -y

# Install dependencies
ARG APT_DEPENDENCIES
RUN apt-get install --no-install-recommends -y $APT_DEPENDENCIES

# Install needed ros packages
ARG ROS_WORKSPACE
COPY $ROS_WORKSPACE/src /tmp/workspace/src/
RUN cd /tmp/workspace && rosdep update && rosdep install --from-paths src --ignore-src -r -y
RUN rm -rf /tmp/workspace

# Install some python packages
ARG PIP_REQUIREMENTS
RUN pip install $PIP_REQUIREMENTS

# Run any user scripts
# Should be used to install additional packages
ARG SCRIPTS_DIR
COPY $SCRIPTS_DIR /tmp/scripts/
RUN for f in /tmp/scripts/*; do [ -x $f ] && [ -f $f ] && $f || continue; done
RUN rm -rf /tmp/scripts

# Clean up to reduce image size
RUN apt-get clean && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Add user and grant sudo permission.
RUN adduser --shell /bin/bash --disabled-password --gecos "" $USERNAME && \
    echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME

# ROS Setup
RUN sed -i 's|source|#source|g' /ros_entrypoint.sh
RUN echo ". /opt/ros/$ROS_DISTRO/setup.sh" >> $USERSHELLPROFILE
RUN echo "[ -f $USERHOME/$PROJECT/workspace/install/setup.$USERSHELL ] && . $USERHOME/$PROJECT/workspace/install/setup.$USERSHELL" >> $USERSHELLPROFILE
RUN /bin/$USERSHELL -c "source /opt/ros/$ROS_DISTRO/setup.$USERSHELL"

# Default bash config
RUN [ "$USERSHELL" = "bash" ] && echo 'export TERM=xterm-256color' >> $USERSHELLPROFILE && echo 'export PS1="\[\033[38;5;40m\]\h\[$(tput sgr0)\]:\[$(tput sgr0)\]\[\033[38;5;39m\]\w\[$(tput sgr0)\]\\$ \[$(tput sgr0)\]"' >> $USERSHELLPROFILE

# Set user and work directory
USER $USERNAME 
WORKDIR $USERHOME

ENV USERSHELLPATH=$USERSHELLPATH
CMD $USERSHELLPATH