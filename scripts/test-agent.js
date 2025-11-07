/**
 * Test Email Agent
 * Test the autonomous email agent with sample emails
 */

const emailAgentSetup = require('../lib/email-agent-setup');

async function testAgent() {
  console.log('🤖 Testing Email Agent\n');

  try {
    // Initialize agent
    console.log('1. Initializing agent...');
    const result = await emailAgentSetup.initialize();
    console.log(`✅ Agent initialized: ${result.agentEmail}`);
    console.log(`   Reasoning model: ${result.capabilities.tools.join(', ')}\n`);

    // Test email 1: Simple information request
    console.log('2. Testing simple information request...');
    const testEmail1 = {
      id: 'test1',
      from: 'user@example.com',
      to: result.agentEmail,
      subject: 'What\'s on my calendar today?',
      body: 'Can you check my calendar and let me know what meetings I have today?',
      date: new Date().toISOString()
    };

    const response1 = await emailAgentSetup.processSingleEmail(testEmail1);
    console.log(`   Result: ${response1.processed ? '✅ Processed' : '❌ Not processed'}`);
    if (response1.understanding) {
      console.log(`   Intent: ${response1.understanding.intent}`);
      console.log(`   Requires action: ${response1.understanding.requiresAction}\n`);
    }

    // Test email 2: Web automation request
    console.log('3. Testing web automation request...');
    const testEmail2 = {
      id: 'test2',
      from: 'user@example.com',
      to: result.agentEmail,
      subject: 'Check website status',
      body: 'Can you navigate to example.com and tell me if it\'s up?',
      date: new Date().toISOString()
    };

    const response2 = await emailAgentSetup.processSingleEmail(testEmail2);
    console.log(`   Result: ${response2.processed ? '✅ Processed' : '❌ Not processed'}`);
    if (response2.understanding) {
      console.log(`   Intent: ${response2.understanding.intent}`);
      console.log(`   Actions: ${response2.understanding.actions?.length || 0}\n`);
    }

    // Show statistics
    console.log('4. Agent statistics:');
    const stats = emailAgentSetup.getStatus();
    console.log(`   Total actions: ${stats.statistics.totalActions}`);
    console.log(`   Success rate: ${stats.statistics.successRate}`);
    console.log(`   Available tools: ${stats.statistics.availableTools.join(', ')}\n`);

    // Show action history
    console.log('5. Action history:');
    const history = emailAgentSetup.getActionHistory(5);
    history.forEach((action, i) => {
      console.log(`   ${i + 1}. ${action.understanding.intent}`);
      console.log(`      Actions: ${action.execution?.results?.length || 0}`);
      console.log(`      Success: ${action.execution?.overallSuccess ? '✅' : '❌'}`);
    });

    console.log('\n✅ Test complete!');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error(error.stack);
  } finally {
    // Cleanup
    await emailAgentSetup.shutdown();
  }
}

// Run test
testAgent();
