#!/bin/bash

# Install uv - fast Python package installer and resolver
if command -v uv &> /dev/null; then
    echo "uv is already installed."
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Add uv to PATH if not already
echo "Current shell: $SHELL"
if [[ "$SHELL" == *"bash"* ]]; then
    if ! command -v uv &> /dev/null; then
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
        source ~/.bashrc
    fi
elif [[ "$SHELL" == *"zsh"* ]]; then
    if ! command -v uv &> /dev/null; then
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
        source ~/.zshrc
    fi
else
    echo "Unsupported shell: $SHELL. Please manually add uv to your PATH."
fi

echo "uv installed successfully!"
echo "You can now use 'sudo uv run main.py' to run the script."
