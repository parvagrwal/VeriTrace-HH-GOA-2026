// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VerificationRegistry {
    struct Record {
        bytes32 recordHash;
        address submitter;
        uint256 timestamp;
    }

    uint256 public recordCount;
    mapping(uint256 => Record) public records;

    event RecordStored(
        uint256 indexed id,
        bytes32 indexed recordHash,
        address indexed submitter,
        uint256 timestamp
    );

    function storeRecord(bytes32 recordHash) external returns (uint256 id) {
        require(recordHash != bytes32(0), "Invalid record hash");

        recordCount++;
        id = recordCount;

        records[id] = Record({
            recordHash: recordHash,
            submitter: msg.sender,
            timestamp: block.timestamp
        });

        emit RecordStored(id, recordHash, msg.sender, block.timestamp);
    }

    function getRecord(uint256 id)
        external
        view
        returns (
            bytes32 recordHash,
            address submitter,
            uint256 timestamp
        )
    {
        require(id > 0 && id <= recordCount, "Record does not exist");
        Record memory rec = records[id];
        return (rec.recordHash, rec.submitter, rec.timestamp);
    }

    function totalRecords() external view returns (uint256) {
        return recordCount;
    }
}
