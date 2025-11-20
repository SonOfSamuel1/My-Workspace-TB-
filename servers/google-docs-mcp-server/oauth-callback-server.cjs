const http = require('http');
const url = require('url');
const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

const CREDENTIALS_PATH = path.join(__dirname, 'credentials.json');
const TOKEN_PATH = path.join(__dirname, 'token.json');
const SCOPES = [
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/drive.readonly',
];

const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf-8'));
const { client_id, client_secret } = credentials.installed;
const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, 'http://localhost:8080');

const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);

  if (parsedUrl.pathname === '/') {
    const code = parsedUrl.query.code;

    if (code) {
      try {
        const { tokens } = await oAuth2Client.getToken(code);
        oAuth2Client.setCredentials(tokens);
        fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens));

        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(`
          <html>
            <body>
              <h1>✓ Authorization Successful!</h1>
              <p>Token has been saved. You can close this window.</p>
              <p>The Google Docs MCP server is now ready to use!</p>
            </body>
          </html>
        `);

        console.log('✓ Token stored successfully!');
        console.log(`Token saved at: ${TOKEN_PATH}`);

        setTimeout(() => {
          server.close();
          process.exit(0);
        }, 2000);
      } catch (error) {
        res.writeHead(500, { 'Content-Type': 'text/html' });
        res.end(`<html><body><h1>Error</h1><p>${error.message}</p></body></html>`);
        console.error('Error retrieving access token', error);
      }
    } else {
      res.writeHead(400, { 'Content-Type': 'text/html' });
      res.end('<html><body><h1>Error</h1><p>No authorization code found</p></body></html>');
    }
  }
});

const PORT = 8080;
server.listen(PORT, () => {
  const authUrl = oAuth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
  });

  console.log('\n📋 Authorize this app by visiting this URL:\n');
  console.log(authUrl + '\n');
  console.log(`Listening on http://localhost:${PORT} for OAuth callback...\n`);
});
