#!/usr/bin/env node

import { google } from "googleapis";
import * as fs from "fs";
import * as path from "path";
import { homedir } from "os";
import * as readline from "readline";

const SCOPES = [
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/gmail.modify",
];

const TOKEN_PATH = path.join(homedir(), ".gmail-mcp-token.json");
const CREDENTIALS_PATH = path.join(homedir(), ".gmail-mcp-credentials.json");

async function authenticate() {
  try {
    // Check if credentials file exists
    if (!fs.existsSync(CREDENTIALS_PATH)) {
      console.error(`
Error: Credentials file not found at ${CREDENTIALS_PATH}

To set up Gmail API credentials:
1. Go to https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the credentials JSON file
6. Save it as ${CREDENTIALS_PATH}

Then run this script again.
      `);
      process.exit(1);
    }

    // Load credentials
    const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, "utf-8"));
    const { client_id, client_secret, redirect_uris } = credentials.installed || credentials.web;

    const oAuth2Client = new google.auth.OAuth2(
      client_id,
      client_secret,
      redirect_uris[0]
    );

    // Generate auth URL
    const authUrl = oAuth2Client.generateAuthUrl({
      access_type: "offline",
      scope: SCOPES,
    });

    console.log("Authorize this app by visiting this URL:");
    console.log(authUrl);
    console.log("");

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    rl.question("Enter the authorization code from that page here: ", async (code) => {
      rl.close();

      try {
        const { tokens } = await oAuth2Client.getToken(code);
        oAuth2Client.setCredentials(tokens);

        // Store the token
        fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens, null, 2));
        console.log(`\nToken stored to ${TOKEN_PATH}`);
        console.log("Authentication successful! You can now use the Gmail MCP server.");
      } catch (error) {
        console.error("Error retrieving access token:", error);
        process.exit(1);
      }
    });
  } catch (error) {
    console.error("Error during authentication:", error);
    process.exit(1);
  }
}

authenticate();
