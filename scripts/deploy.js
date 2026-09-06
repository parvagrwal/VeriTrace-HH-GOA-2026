const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("==================================================");
  console.log(" Deploying VerificationRegistry to:", hre.network.name);
  if (deployer) {
    console.log(" Deployer Account:", deployer.address);
    const balance = await hre.ethers.provider.getBalance(deployer.address);
    console.log(" Account Balance:", hre.ethers.formatEther(balance), "POL");
  }
  console.log("==================================================");

  const VerificationRegistry = await hre.ethers.getContractFactory("VerificationRegistry");
  const registry = await VerificationRegistry.deploy();

  await registry.waitForDeployment();
  const contractAddress = await registry.getAddress();

  console.log(">>> VerificationRegistry deployed successfully!");
  console.log(">>> Contract Address:", contractAddress);
  if (hre.network.name === "amoy") {
    console.log(">>> Explorer Link: https://amoy.polygonscan.com/address/" + contractAddress);
  }

  // Export contract address and ABI for Python web3.py integration
  const artifact = await hre.artifacts.readArtifact("VerificationRegistry");
  const deploymentData = {
    address: contractAddress,
    network: hre.network.name,
    chainId: (await hre.ethers.provider.getNetwork()).chainId.toString(),
    abi: artifact.abi,
    deployedAt: new Date().toISOString(),
  };

  const outputPath = path.join(__dirname, "..", "contracts", "deployed_contract.json");
  fs.writeFileSync(outputPath, JSON.stringify(deploymentData, null, 2));
  console.log(">>> Saved deployment artifact to:", outputPath);
  console.log(">>> Update your .env file with:");
  console.log(`CONTRACT_ADDRESS=${contractAddress}`);
  console.log("==================================================");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
