
 // SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MeasurementRegistry {
    address public owner;

    struct MeasurementRecord {
        bytes32 payloadHash;
        address submitter;
        uint64 sourceTimestamp;
        uint64 recordedAt;
        bool exists;
    }

    mapping(address => bool) public authorizedWriters;

    mapping(bytes32 => mapping(uint32 => MeasurementRecord))
        private records;

    event WriterAuthorizationChanged(
        address indexed writer,
        bool authorized
    );

    event MeasurementRecorded(
        bytes32 indexed batchId,
        uint32 indexed measurementIndex,
        bytes32 payloadHash,
        address indexed submitter,
        uint64 sourceTimestamp,
        uint64 recordedAt
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyAuthorizedWriter() {
        require(
            authorizedWriters[msg.sender],
            "Writer not authorized"
        );
        _;
    }

    constructor() {
        owner = msg.sender;
        authorizedWriters[msg.sender] = true;
        emit WriterAuthorizationChanged(msg.sender, true);
    }

    function setWriter(address writer, bool authorized)
        external
        onlyOwner
    {
        require(writer != address(0), "Invalid writer");
        authorizedWriters[writer] = authorized;
        emit WriterAuthorizationChanged(writer, authorized);
    }

    function recordMeasurement(
        bytes32 batchId,
        uint32 measurementIndex,
        bytes32 payloadHash,
        uint64 sourceTimestamp
    ) external onlyAuthorizedWriter {
        require(batchId != bytes32(0), "Invalid batch ID");
        require(payloadHash != bytes32(0), "Invalid hash");
        require(sourceTimestamp > 0, "Invalid timestamp");
        require(
            !records[batchId][measurementIndex].exists,
            "Measurement already recorded"
        );

        uint64 recordedAt = uint64(block.timestamp);

        records[batchId][measurementIndex] = MeasurementRecord({
            payloadHash: payloadHash,
            submitter: msg.sender,
            sourceTimestamp: sourceTimestamp,
            recordedAt: recordedAt,
            exists: true
        });

        emit MeasurementRecorded(
            batchId,
            measurementIndex,
            payloadHash,
            msg.sender,
            sourceTimestamp,
            recordedAt
        );
    }

    function verifyMeasurement(
        bytes32 batchId,
        uint32 measurementIndex,
        bytes32 payloadHash
    ) external view returns (bool) {
        MeasurementRecord storage record =
            records[batchId][measurementIndex];

        return record.exists && record.payloadHash == payloadHash;
    }

    function getMeasurement(
        bytes32 batchId,
        uint32 measurementIndex
    )
        external
        view
        returns (
            bytes32 payloadHash,
            address submitter,
            uint64 sourceTimestamp,
            uint64 recordedAt,
            bool exists
        )
    {
        MeasurementRecord storage record =
            records[batchId][measurementIndex];

        return (
            record.payloadHash,
            record.submitter,
            record.sourceTimestamp,
            record.recordedAt,
            record.exists
        );
    }
}