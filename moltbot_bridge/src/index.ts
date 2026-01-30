import axios from 'axios';

async function main() {
  const resp = await axios.get('http://localhost:8001/health').catch(() => ({data:{ok:false}}));
  console.log('trading_core health:', resp.data);
}

main();
