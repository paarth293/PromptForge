from backend.app.core.hash_chain import create_block, generate_composite_fingerprint, verify_chain


def test_hash_chain_creation_and_verification():
    b0 = create_block({"event": "GENESIS_SPEC", "spec_id": "spec-1"}, prev_hash="GENESIS")
    b1 = create_block({"event": "BLUEPRINT_BUILT", "version": 1}, prev_hash=b0.block_hash)
    b2 = create_block({"event": "RED_TEAM_DONE", "survival": 0.90}, prev_hash=b1.block_hash)

    chain = [b0, b1, b2]
    is_valid, failed_idx, err = verify_chain(chain)
    assert is_valid is True
    assert failed_idx is None
    assert err is None

def test_hash_chain_tamper_detection_in_payload():
    b0 = create_block({"event": "GENESIS_SPEC", "spec_id": "spec-1"}, prev_hash="GENESIS")
    b1 = create_block({"event": "BLUEPRINT_BUILT", "version": 1}, prev_hash=b0.block_hash)
    b2 = create_block({"event": "RED_TEAM_DONE", "survival": 0.90}, prev_hash=b1.block_hash)

    chain = [b0, b1, b2]

    # Tamper with block 1 payload
    b1.payload["version"] = 999  # Unauthorized modification
    is_valid, failed_idx, err = verify_chain(chain)
    assert is_valid is False
    assert failed_idx == 1
    assert "Tamper detected at block 1" in err

def test_hash_chain_broken_link():
    b0 = create_block({"event": "GENESIS_SPEC"}, prev_hash="GENESIS")
    b1 = create_block({"event": "STEP_1"}, prev_hash=b0.block_hash)
    b2 = create_block({"event": "STEP_2"}, prev_hash="invalid_prev_hash_123")

    chain = [b0, b1, b2]
    is_valid, failed_idx, err = verify_chain(chain)
    assert is_valid is False
    assert failed_idx == 2
    assert "prev_hash does not match prior block hash" in err

def test_composite_fingerprint():
    fp1 = generate_composite_fingerprint("bp1", "rt1", "sc1", "aud1")
    fp2 = generate_composite_fingerprint("bp1", "rt1", "sc1", "aud1")
    fp_different = generate_composite_fingerprint("bp2", "rt1", "sc1", "aud1")

    assert fp1 == fp2
    assert fp1 != fp_different
    assert len(fp1) == 64  # SHA-256 hex length
