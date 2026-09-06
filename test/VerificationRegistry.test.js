const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VerificationRegistry Smart Contract", function () {
  let registry;
  let owner;
  let addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const VerificationRegistry = await ethers.getContractFactory("VerificationRegistry");
    registry = await VerificationRegistry.deploy();
    await registry.waitForDeployment();
  });

  it("Should initialize with zero records", async function () {
    expect(await registry.recordCount()).to.equal(0);
    expect(await registry.totalRecords()).to.equal(0);
  });

  it("Should store record and emit RecordStored event", async function () {
    const testHash = ethers.keccak256(ethers.toUtf8Bytes("test-record-content"));

    await expect(registry.connect(addr1).storeRecord(testHash))
      .to.emit(registry, "RecordStored")
      .withArgs(1, testHash, addr1.address, (await ethers.provider.getBlock("latest")).timestamp + 1);

    expect(await registry.recordCount()).to.equal(1);
    expect(await registry.totalRecords()).to.equal(1);

    const record = await registry.getRecord(1);
    expect(record.recordHash).to.equal(testHash);
    expect(record.submitter).to.equal(addr1.address);
    expect(record.timestamp).to.be.gt(0);
  });

  it("Should reject zero hash", async function () {
    const zeroHash = ethers.ZeroHash;
    await expect(registry.storeRecord(zeroHash)).to.be.revertedWith("Invalid record hash");
  });

  it("Should auto-increment record ID across multiple submissions", async function () {
    const hash1 = ethers.keccak256(ethers.toUtf8Bytes("rec1"));
    const hash2 = ethers.keccak256(ethers.toUtf8Bytes("rec2"));

    await registry.storeRecord(hash1);
    await registry.storeRecord(hash2);

    expect(await registry.recordCount()).to.equal(2);
    const rec1 = await registry.getRecord(1);
    const rec2 = await registry.getRecord(2);

    expect(rec1.recordHash).to.equal(hash1);
    expect(rec2.recordHash).to.equal(hash2);
  });

  it("Should revert when querying non-existent record ID", async function () {
    await expect(registry.getRecord(999)).to.be.revertedWith("Record does not exist");
    await expect(registry.getRecord(0)).to.be.revertedWith("Record does not exist");
  });
});
