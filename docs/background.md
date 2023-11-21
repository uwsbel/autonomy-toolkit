# Background

This page provides some helpful background about the `autonomy-toolkit`.

## Design Considerations

The _most_ important component we considered when creating the this package was whether the workflow was usable on multiple platforms/use cases, i.e. it would work as is on Windows, MacOS, Linux, and multi-user systems. This was a non-negotiable because we could be developing anywhere and on any machine and we don't want to require any special hardware or "hacking" to work on a specific system (unless the system itself requires it, but we don't). For instance, the primary advantage of a docker-based development workflow is that it reduces the "It works on my machine" bottleneck; if you have docker installed, you can duplicate a setup exactly. This is advantageous for many reasons, but most so as an internal tool to mitigate "hacking things together".

Another important element we considered was orchestration. This page won't do a deep dive on docker compose, but generally speaking, orchestration is a powerful mechanism which allows multiple, configurable, and independent systems to be run at the same time and work together to accomplish some goal. A simple example is a database system: docker compose can be employed to spin up a database which holds some data (system #1) and a frontend which queries the database (system #2). `autonomy-toolkit` doesn't directly invoke this workflow, that's handled by docker compose, but this was the basis for which we chose to use docker compose in the first place.

## Docker

To begin, Docker is a tool for virtualizing applications from a main operating system. What this means is that you can run full OS containers within a host OS. The primary purpose behind Docker, and similar tools, is to isolate development environments and to consistently deploy applications across computers. Docker is commonly used on servers (think AWS or Azure) to isolate users and to deploy websites and web apps. Docker simply provides the ability to run these isolated containers, it is the users job to create the content that goes inside the containers. For more information on Docker, please see their [official website](https://www.docker.com/).