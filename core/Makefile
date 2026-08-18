CC = gcc
CFLAGS = -Wall -fPIC
LDFLAGS = -shared -ltag_c -lm -lpthread -ldl

TARGET = libplayer.so
SRCS = player.c scanner.c json_builder.c

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) $(SRCS) -o $(TARGET) $(LDFLAGS)

deps:
	@echo "Installing system dependencies..."
	@if command -v apt-get >/dev/null 2>&1; then \
		sudo apt-get update; \
		sudo apt-get install -y gcc make libvlc-dev libtagc0-dev python3 python3-pip npm; \
	elif command -v pacman >/dev/null 2>&1; then \
		sudo pacman -Sy --noconfirm gcc make vlc taglib python python-pip npm; \
	elif command -v dnf >/dev/null 2>&1; then \
		sudo dnf install -y gcc make vlc-devel taglib-devel python3 python3-pip npm; \
	else \
		echo "Unsupported package manager. Please install gcc, libvlc-dev, libtagc0-dev, python3, pip, and npm manually."; \
		exit 1; \
	fi
	@echo "Installing Python dependencies..."
	python3 -m pip install pywebview --break-system-packages || true
	@echo "Installing NPM dependencies..."
	cd .. && npm install

clean:
	rm -f $(TARGET)
