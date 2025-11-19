/**
 * Interactive Email Agent Demo
 * See the agent in action with sample requests
 */

const emailAgentSetup = require('../lib/email-agent-setup');

// Demo email requests
const demoEmails = [
  {
    id: 'demo1',
    from: 'user@example.com',
    to: 'assistant@yourdomain.com',
    subject: 'Quick question',
    body: 'What is the current time?',
    date: new Date().toISOString(),
    description: 'Simple information request'
  },
  {
    id: 'demo2',
    from: 'user@example.com',
    to: 'assistant@yourdomain.com',
    subject: 'Website check',
    body: 'Can you navigate to example.com and tell me if the website is up and what the main heading says?',
    date: new Date().toISOString(),
    description: 'Web automation with Playwright'
  },
  {
    id: 'demo3',
    from: 'user@example.com',
    to: 'assistant@yourdomain.com',
    subject: 'Data analysis',
    body: 'Can you analyze this sales data and extract key metrics?\n\nQ4 2024 Results:\n- Total Revenue: $1.2M\n- New Customers: 45\n- Retention Rate: 92%',
    date: new Date().toISOString(),
    description: 'Data processing'
  }
];

async function runDemo() {
  console.log('\n╔════════════════════════════════════════════════════════════╗');
  console.log('║         📧 Email Agent Interactive Demo 🤖                 ║');
  console.log('╚════════════════════════════════════════════════════════════╝\n');

  try {
    // Check environment
    console.log('🔍 Checking environment configuration...\n');

    if (!process.env.OPENROUTER_API_KEY) {
      console.log('⚠️  OPENROUTER_API_KEY not set');
      console.log('   The demo will run in mock mode (no actual AI calls)\n');
    } else {
      console.log('✅ OpenRouter API key found');
    }

    if (!process.env.AGENT_EMAIL) {
      console.log('ℹ️  Using default agent email: assistant@yourdomain.com\n');
    } else {
      console.log(`✅ Agent email: ${process.env.AGENT_EMAIL}\n`);
    }

    // Initialize agent
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    console.log('📋 STEP 1: Initializing Email Agent\n');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    const result = await emailAgentSetup.initialize();

    console.log(`✅ Agent Email: ${result.agentEmail}`);
    console.log(`✅ Reasoning Model: ${result.capabilities.model || 'Mock mode'}`);
    console.log(`✅ Available Tools: ${result.capabilities.tools.join(', ')}`);
    console.log(`✅ Safety Mode: ${result.capabilities.safetyMode ? 'Enabled' : 'Disabled'}\n`);

    // Process demo emails
    for (let i = 0; i < demoEmails.length; i++) {
      const email = demoEmails[i];

      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
      console.log(`📧 DEMO ${i + 1}/3: ${email.description}\n`);
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

      console.log(`From: ${email.from}`);
      console.log(`Subject: ${email.subject}`);
      console.log(`Body: ${email.body}\n`);

      console.log('⏳ Processing email...\n');

      try {
        const response = await emailAgentSetup.processSingleEmail(email);

        if (response.processed) {
          console.log('✅ Email processed successfully!\n');

          if (response.understanding) {
            console.log('🧠 Understanding:');
            console.log(`   Intent: ${response.understanding.intent}`);
            console.log(`   Requires Action: ${response.understanding.requiresAction ? 'Yes' : 'No'}`);

            if (response.understanding.actions && response.understanding.actions.length > 0) {
              console.log(`   Planned Actions: ${response.understanding.actions.length}`);
              response.understanding.actions.forEach((action, idx) => {
                console.log(`      ${idx + 1}. ${action.type} (${action.tool})`);
              });
            }
            console.log();
          }

          if (response.execution) {
            console.log('⚙️  Execution:');
            console.log(`   Overall Success: ${response.execution.overallSuccess ? '✅' : '❌'}`);

            if (response.execution.results && response.execution.results.length > 0) {
              console.log(`   Results:`);
              response.execution.results.forEach((result, idx) => {
                console.log(`      ${idx + 1}. ${result.success ? '✅' : '❌'} ${result.action || 'Action'}`);
                if (result.data) {
                  console.log(`         Data: ${JSON.stringify(result.data).substring(0, 100)}...`);
                }
              });
            }
            console.log();
          }

          if (response.response) {
            console.log('📤 Response Email:');
            console.log('   ───────────────────────────────────────────────────');
            console.log(`   ${response.response.body}`);
            console.log('   ───────────────────────────────────────────────────');
            console.log();
          }

        } else {
          console.log(`⚠️  Email not processed: ${response.reason || 'Unknown reason'}\n`);
        }

      } catch (error) {
        console.log(`❌ Error processing email: ${error.message}\n`);
      }

      // Pause between demos
      if (i < demoEmails.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    // Show final statistics
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    console.log('📊 AGENT STATISTICS\n');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    const status = emailAgentSetup.getStatus();
    console.log(`Total Actions Executed: ${status.statistics.totalActions}`);
    console.log(`Success Rate: ${status.statistics.successRate}`);
    console.log(`Tools Available: ${status.statistics.availableTools.join(', ')}\n`);

    const history = emailAgentSetup.getActionHistory(10);
    console.log(`Recent Action History (${history.length} actions):`);
    history.forEach((action, idx) => {
      console.log(`   ${idx + 1}. ${action.understanding.intent}`);
      console.log(`      Success: ${action.execution?.overallSuccess ? '✅' : '❌'}`);
      console.log(`      Timestamp: ${new Date(action.timestamp).toLocaleString()}`);
    });

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    console.log('✅ Demo Complete!\n');
    console.log('To use the agent in production:');
    console.log('1. Set OPENROUTER_API_KEY in your .env file');
    console.log('2. Set AGENT_EMAIL to your dedicated agent address');
    console.log('3. Configure Gmail MCP to monitor the agent inbox');
    console.log('4. Send emails to the agent address to trigger actions\n');

  } catch (error) {
    console.error('\n❌ Demo failed:', error.message);
    console.error(error.stack);
  } finally {
    // Cleanup
    await emailAgentSetup.shutdown();
    console.log('🔌 Agent shutdown complete\n');
  }
}

// Handle errors
process.on('unhandledRejection', (error) => {
  console.error('Unhandled error:', error);
  process.exit(1);
});

// Run demo
console.log('\nStarting demo in 2 seconds...\n');
setTimeout(runDemo, 2000);
