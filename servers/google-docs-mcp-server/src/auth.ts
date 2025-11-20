#!/usr/bin/env node

/**
 * Google OAuth2 Authentication Helper
 *
 * This script helps you obtain OAuth2 tokens for the Google Docs API.
 * Run this once to generate a token.json file that the MCP server will use.
 */

import { google } from "googleapis";
import * as fs from "fs";
import * as path from "path";
import * as readline from "readline";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// If modifying these scopes, delete token.json and re-authorize
const SCOPES = [
  "https://www.googleapis.com/auth/documents",
  "https://www.googleapis.com/auth/drive.readonly",
];

const CREDENTIALS_PATH = path.join(__dirname, "../credentials.json");
const TOKEN_PATH = path.join(__dirname, "../token.json");

async function authorize() {
  if (!fs.existsSync(CREDENTIALS_PATH)) {
    console.error("Error: credentials.json not found!");
    console.error("\nPlease follow these steps:");
    console.error("1. Go to https://console.cloud.google.com/");
    console.error("2. Create a new project or select an existing one");
    console.error("3. Enable the Google Docs API and Google Drive API");
    console.error("4. Create OAuth 2.0 credentials (Desktop app)");
    console.error("5. Download the credentials and save as credentials.json");
    console.error(`6. Place credentials.json at: ${CREDENTIALS_PATH}`);
    process.exit(1);
  }

  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, "utf-8"));
  const { client_id, client_secret, redirect_uris } = credentials.installed || credentials.web;

  const oAuth2Client = new google.auth.OAuth2(
    client_id,
    client_secret,
    redirect_uris[0]
  );

  // Check if we already have a token
  if (fs.existsSync(TOKEN_PATH)) {
    const token = JSON.parse(fs.readFileSync(TOKEN_PATH, "utf-8"));
    oAuth2Client.setCredentials(token);
    console.log("✓ Token already exists and is valid!");
    console.log(`Token saved at: ${TOKEN_PATH}`);
    return;
  }

  // Get new token
  const authUrl = oAuth2Client.generateAuthUrl({
    access_type: "offline",
    scope: SCOPES,
  });

  console.log("\n📋 Authorize this app by visiting this URL:");
  console.log("\n" + authUrl + "\n");

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  rl.question("Enter the code from that page here: ", (code) => {
    rl.close();
    oAuth2Client.getToken(code, (err, token) => {
      if (err) {
        console.error("Error retrieving access token", err);
        return;
      }
      if (token) {
        oAuth2Client.setCredentials(token);
        fs.writeFileSync(TOKEN_PATH, JSON.stringify(token));
        console.log("\n✓ Token stored successfully!");
        console.log(`Token saved at: ${TOKEN_PATH}`);
        console.log("\nYou can now use the Google Docs MCP server!");
      }
    });
  });
}

authorize().catch(console.error);
