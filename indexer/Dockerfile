FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install rindexer
RUN curl -L https://rindexer.xyz/install.sh | bash
ENV PATH="/root/.rindexer/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy rindexer configuration and ABIs
COPY rindexer/ ./

# Expose any ports if needed (rindexer GraphQL typically runs on 3001)
EXPOSE 3001

# Default command - can be overridden
CMD ["rindexer", "start", "indexer"]