/**
 * Google OAuth Authorization Script
 *
 * Run this once to generate a token.json file for calendar access.
 * Usage: node authorize.js
 */

const { google } = require("googleapis");
const fs = require("fs");
const path = require("path");
const http = require("http");
const url = require("url");

const CREDENTIALS_PATH = path.join(__dirname, "credentials", "credentials.json");
const TOKEN_PATH = path.join(__dirname, "credentials", "token.json");
const SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"];

async function authorize() {
  // Load credentials
  if (!fs.existsSync(CREDENTIALS_PATH)) {
    console.error("❌ credentials.json not found at:", CREDENTIALS_PATH);
    console.log("\nTo get credentials:");
    console.log("1. Go to https://console.cloud.google.com/");
    console.log("2. Create a project or select existing one");
    console.log("3. Enable Google Calendar API");
    console.log("4. Create OAuth 2.0 credentials (Desktop app)");
    console.log("5. Download and save as credentials/credentials.json");
    process.exit(1);
  }

  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, "utf8"));
  const { client_id, client_secret, redirect_uris } =
    credentials.installed || credentials.web;

  const oAuth2Client = new google.auth.OAuth2(
    client_id,
    client_secret,
    "http://localhost:3000/oauth2callback"
  );

  // Check for existing token
  if (fs.existsSync(TOKEN_PATH)) {
    const token = JSON.parse(fs.readFileSync(TOKEN_PATH, "utf8"));
    oAuth2Client.setCredentials(token);

    // Test if token is valid
    try {
      const calendar = google.calendar({ version: "v3", auth: oAuth2Client });
      await calendar.calendarList.list({ maxResults: 1 });
      console.log("✅ Existing token is valid!");
      console.log("Token saved at:", TOKEN_PATH);
      return;
    } catch (error) {
      console.log("Existing token expired, refreshing...");
    }
  }

  // Generate auth URL
  const authUrl = oAuth2Client.generateAuthUrl({
    access_type: "offline",
    scope: SCOPES,
    prompt: "consent",
  });

  console.log("\n🔐 Authorization Required\n");
  console.log("Opening browser for authorization...\n");
  console.log("If browser doesn't open, visit this URL:\n");
  console.log(authUrl);
  console.log("\n");

  // Open browser
  const open = (await import("open")).default;
  await open(authUrl);

  // Start local server to receive callback
  return new Promise((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      try {
        const parsedUrl = url.parse(req.url, true);

        if (parsedUrl.pathname === "/oauth2callback") {
          const code = parsedUrl.query.code;

          if (!code) {
            res.writeHead(400);
            res.end("No authorization code received");
            reject(new Error("No authorization code"));
            return;
          }

          // Exchange code for tokens
          const { tokens } = await oAuth2Client.getToken(code);
          oAuth2Client.setCredentials(tokens);

          // Save token
          fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens, null, 2));

          res.writeHead(200, { "Content-Type": "text/html" });
          res.end(`
            <html>
              <body style="font-family: system-ui; text-align: center; padding-top: 50px;">
                <h1>✅ Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
              </body>
            </html>
          `);

          console.log("\n✅ Authorization successful!");
          console.log("Token saved at:", TOKEN_PATH);

          server.close();
          resolve(tokens);
        }
      } catch (error) {
        res.writeHead(500);
        res.end("Error: " + error.message);
        reject(error);
      }
    });

    server.listen(3000, () => {
      console.log("Waiting for authorization callback on http://localhost:3000...");
    });

    // Timeout after 5 minutes
    setTimeout(() => {
      server.close();
      reject(new Error("Authorization timed out"));
    }, 300000);
  });
}

authorize()
  .then(() => {
    console.log("\n🎉 You can now run: npm test");
    process.exit(0);
  })
  .catch((error) => {
    console.error("\n❌ Authorization failed:", error.message);
    process.exit(1);
  });
