# WebSocket Documentation

## Overview
This document provides detailed information on how to connect to and use the WebSocket endpoints provided by this Django project. It covers authentication, connection URLs, and message formats.

## WebSocket Endpoints

### User Feed WebSocket
- **URL**: `ws://<your-domain>/ws/feed/user/<user_id>/?token=<your_token>`
- **Description**: Connect to this WebSocket to receive real-time updates to the user's feed.

#### Example Connection
```javascript
const userFeedUrl = `ws://your-domain/ws/feed/user/${user_id}/?token=${token}`;
const userFeedSocket = new WebSocket(userFeedUrl);

userFeedSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    console.log('User Feed Update:', data);
    // Handle the update
};
