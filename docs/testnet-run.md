# Running the swap stack on public testnets

This guide runs the Maker and Taker Nodes, and both Basecamp desks, against
the **official LEZ v0.2 testnet** (`https://testnet.lez.logos.co`, channel
`0101…01`, LEZ v0.2.4) and **Bitcoin testnet4**. Nothing here is a local
chain: four local services join the public networks, and the Nodes reach
them over a Docker network.

| Service | What it is | Why it runs locally |
|---|---|---|
| `lez-btc-testnet4` | Bitcoin Core 31.1 on testnet4, unpruned, `txindex` + `txospenderindex` | the Nodes' Bitcoin adapter needs both indexes and a wallet per role |
| `lez-testnet-node` | Logos Blockchain node on the public testnet | feeds the indexer |
| `lez-testnet-indexer` | LEZ v0.2.4 indexer following the public channel | the public endpoint serves no indexer (`getLastFinalizedBlockId`) |
| `lez-testnet-sequencer` | nginx: plain HTTP on the Docker network to `https://testnet.lez.logos.co` | the Nodes accept only literal-loopback HTTP endpoints |

Host requirements: arm64 with Docker, about 40 GB for testnet4 and room for
the Logos Blockchain node's state.

## 1. Shared network

```sh
docker network create lez-testnet
mkdir -p ~/lez-testnet
```

## 2. Bitcoin testnet4

```sh
D=~/lez-testnet; umask 077
printf 'BTC_TESTNET4_RPC_USER=lezrpc\nBTC_TESTNET4_RPC_PASSWORD=%s\n' "$(openssl rand -hex 24)" > $D/btc-testnet4-rpc.env
. $D/btc-testnet4-rpc.env
cat > $D/bitcoin-testnet4.conf <<CONF
chain=testnet4
server=1
txindex=1
txospenderindex=1
prune=0
dbcache=2048
[testnet4]
rpcbind=0.0.0.0
rpcport=18443
rpcallowip=0.0.0.0/0
rpcuser=$BTC_TESTNET4_RPC_USER
rpcpassword=$BTC_TESTNET4_RPC_PASSWORD
CONF
chmod 644 $D/bitcoin-testnet4.conf; mkdir -p $D/bitcoin-testnet4; chmod 777 $D/bitcoin-testnet4
docker run -d --name lez-btc-testnet4 --restart unless-stopped --network lez-testnet \
  -p 127.0.0.1:48332:18443 -v $D/bitcoin-testnet4:/var/lib/bitcoin -v $D:/run-config-dir:ro \
  lez-bitcoin-core:local -conf=/run-config-dir/bitcoin-testnet4.conf -datadir=/var/lib/bitcoin -printtoconsole
```

The initial sync took under an hour on Apple silicon. Stop the node with
`docker stop -t 300 lez-btc-testnet4`; a forced removal loses the unflushed
cache and the node re-syncs tens of thousands of blocks.

Create one wallet per role (`lez-maker`, `lez-taker`) with `createwallet` and
fund each from a testnet4 faucet. Every public testnet4 faucet found requires a
captcha or a login, so this step needs a person; about 30,000 sats per wallet
covers a swap in each direction. Mining is not an option: minimum-difficulty
blocks are taken the moment they become valid.

## 3. The public Logos Blockchain node

Use the `testnet` image; the `0.2.4` release image speaks a different chain-sync
protocol (`dst-0.2.4`) and the bootstrap peers refuse it.

```sh
N=~/lez-testnet/logos-node; I=ghcr.io/logos-blockchain/logos-blockchain:testnet
mkdir -p $N/state; chmod 777 $N $N/state
docker run --rm --user 65532:65532 -e HOME=/tmp -v $N:/cfg --entrypoint /usr/bin/logos-blockchain-node $I \
  init-config -o /cfg/user_config.yaml -p \
  /ip4/65.109.51.37/udp/3000/quic-v1/p2p/12D3KooWFrouXfmrR4nsLMtE7wu15DoMJ6VtoUtHinREZCvbWHar \
  /ip4/65.109.51.37/udp/3001/quic-v1/p2p/12D3KooWJRGau8M1rjT7R5e4YYsgdFhsMX35nRDtMwCDjxQkXAHz \
  /ip4/65.109.51.37/udp/3002/quic-v1/p2p/12D3KooWQXJavMDTRscjauFSgVAB1VLB6Rzpy2uY5SU9Tk7927tb \
  /ip4/65.109.51.37/udp/50001/quic-v1/p2p/12D3KooWSQc7CcGtvWDPF1yCbBthFnQjprfCVHmfmNDUrSmqQsU1
sed -i.bak 's/listen_address: 127.0.0.1:8080/listen_address: 0.0.0.0:8080/' $N/user_config.yaml
docker run -d --name lez-testnet-node --restart unless-stopped --network lez-testnet --user 65532:65532 \
  -e HOME=/tmp -w /cfg -v $N:/cfg -p 127.0.0.1:28080:8080 -p 3000:3000/udp \
  --entrypoint /usr/bin/logos-blockchain-node $I /cfg/user_config.yaml
curl -s http://127.0.0.1:28080/cryptarchia/info
```

The bootstrap peers are those in the Logos Blockchain Node 0.2.4 release notes.

## 4. The sequencer proxy

```sh
mkdir -p ~/lez-testnet/proxy
# nginx.conf: listen 3040; proxy_pass https://testnet.lez.logos.co with
# proxy_set_header Host testnet.lez.logos.co, proxy_ssl_server_name on,
# proxy_ssl_verify on, proxy_ssl_verify_depth 4 (the chain has four certificates),
# proxy_ssl_trusted_certificate /etc/ssl/cert.pem.
docker run -d --name lez-testnet-sequencer --restart unless-stopped --network lez-testnet \
  -p 127.0.0.1:23040:3040 -v ~/lez-testnet/proxy:/etc/nginx/lez:ro \
  nginx:1.29.1-alpine nginx -c /etc/nginx/lez/nginx.conf -g 'daemon off;'
```

Mount the configuration directory, not the file, so an edit survives a restart.

## 5. The indexer

Build `indexer_service` from LEZ v0.2.4 (`47eba25`; its testnet genesis is
enabled by default) and run it against the local node:

```sh
cat > ~/lez-testnet/indexer/indexer_config.json <<JSON
{
  "consensus_info_polling_interval": "1s",
  "bedrock_config": { "addr": "http://lez-testnet-node:8080" },
  "channel_id": "0101010101010101010101010101010101010101010101010101010101010101",
  "allow_chain_reset": true
}
JSON
docker run -d --name lez-testnet-indexer --restart unless-stopped --network lez-testnet \
  -p 127.0.0.1:28779:8779 --user 65532:65532 -e HOME=/tmp -v <dir with indexer_service>:/opt/lez:ro \
  -v ~/lez-testnet/indexer:/cfg --entrypoint /opt/lez/indexer_service lez-services:local \
  /cfg/indexer_config.json --port 8779 --data-dir /cfg/state
```

The indexer serves no finalized block until the node leaves its prolonged
bootstrap period.

## 6. LEZ accounts and funds

The Nodes' identity keys (`lez-v02-local-actor-identity`) work unchanged on
the public network. Fund each role's owner account with the LEZ v0.2.4 wallet
CLI (it links `libpcsclite`):

```sh
export LEE_WALLET_HOME_DIR=~/lez-testnet/wallet-home
wallet change-network testnet
wallet account import public --private-key "$(cat <identity>/lez-signer.key)"
wallet auth-transfer init --account-id Public/<account id>
wallet pinata claim --to Public/<account id>      # 150 LEZ per claim, no captcha
```

`All pollers failed` from the wallet is a poll timeout; confirm with the
sequencer's `getAccount` or the explorer
(`https://explorer.testnet.lez.logos.co/account/<id>`).

## 7. The escrow program

The official sequencer admits at most **614,200 bytes** per transaction, and a
program deployment carries the whole risc0 program binary. The escrow guest
built with default settings is 685,524 bytes: 198 KB of it are symbol and
string tables the zkVM never loads. The guest crate therefore strips symbols
in its release profile (`escrow/methods/guest/Cargo.toml`); the loaded image,
and so the ImageID, does not depend on them.

Deploy through the sequencer proxy's network namespace, where
`http://127.0.0.1:3040/` is the official sequencer, which is the only kind of
endpoint the deployer accepts:

```sh
docker run --rm --network container:lez-testnet-sequencer \
  -v <dir with lez-zec-escrow-v02-deployer>:/deployer:ro -v ~/lez-testnet/market/bootstrap:/out \
  lez-builder:local bash -c '/deployer/lez-zec-escrow-v02-deployer deploy-m4-local \
    --rpc-url http://127.0.0.1:3040/ \
    --channel-id 0101010101010101010101010101010101010101010101010101010101010101 \
    --timeout-seconds 900 > /out/deployment.json'
```

Its preflight checks the channel and the live builtin program ids
(`authenticated_transfer` `fe96c422…`, `token` `ccc4713e…`, and the
associated-token-account ImageID `9df1315d…`, which `getProgramIds` omits)
before it submits anything.
