import pickle
import json
import os
from pathlib import Path

class ContractManager:
    """Manages multiple airline contracts"""
    
    def __init__(self, contracts_dir='contracts'):
        self.contracts_dir = contracts_dir
        self.contracts = {}
        self.load_all_contracts()
    
    def load_all_contracts(self):
        """Load metadata for all available contracts"""
        contracts_path = Path(self.contracts_dir)
        
        if not contracts_path.exists():
            print(f"Warning: {self.contracts_dir} directory not found")
            return
        
        for contract_dir in contracts_path.iterdir():
            if contract_dir.is_dir():
                metadata_file = contract_dir / 'metadata.json'
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        self.contracts[metadata['contract_id']] = metadata
                        print(f"  ✓ Loaded {metadata['airline_name']} ({metadata['contract_id']})")
    
    def get_available_contracts(self):
        """Get list of all available contracts"""
        return {k: v for k, v in self.contracts.items() if v.get('active', True)}
    
    def get_contract_info(self, contract_id):
        """Get metadata for specific contract"""
        return self.contracts.get(contract_id)
    
    def load_contract_data(self, contract_id):
        """Load chunks and embeddings for a specific contract"""
        if contract_id not in self.contracts:
            raise ValueError(f"Contract {contract_id} not found")
        
        contract_path = Path(self.contracts_dir) / contract_id
        
        # Load chunks
        chunks_file = contract_path / 'chunks.pkl'
        if not chunks_file.exists():
            raise FileNotFoundError(f"Chunks file not found for {contract_id}")
        
        with open(chunks_file, 'rb') as f:
            chunks = pickle.load(f)
        
        # Load embeddings
        embeddings_file = contract_path / 'embeddings.pkl'
        if not embeddings_file.exists():
            raise FileNotFoundError(f"Embeddings file not found for {contract_id}")
        
        with open(embeddings_file, 'rb') as f:
            embeddings = pickle.load(f)
        
        return chunks, embeddings
    
    def get_contract_text(self, contract_id):
        """Load full contract text"""
        contract_path = Path(self.contracts_dir) / contract_id
        text_file = contract_path / 'contract_text.txt'
        
        if not text_file.exists():
            return None
        
        with open(text_file, 'r', encoding='utf-8') as f:
            return f.read()

# Test the contract manager
if __name__ == "__main__":
    print("="*70)
    print("TESTING CONTRACT MANAGER")
    print("="*70)
    
    manager = ContractManager()
    
    print("\nAvailable contracts:")
    for contract_id, info in manager.get_available_contracts().items():
        print(f"  - {info['airline_name']} ({contract_id})")
        print(f"    Pages: {info['total_pages']}")
        print(f"    Version: {info['contract_version']}")
        print(f"    Price: ${info['price_per_month']}/month")
    
    # Test loading NAC
    print("\n" + "="*70)
    print("TESTING NAC CONTRACT LOADING")
    print("="*70)
    
    try:
        chunks, embeddings = manager.load_contract_data('NAC')
        print(f"\n✓ Successfully loaded NAC contract:")
        print(f"  Chunks: {len(chunks)}")
        print(f"  Embeddings: {len(embeddings)}")
        
        # Verify data structure
        if len(chunks) > 0:
            print(f"  First chunk ID: {chunks[0]['id']}")
            print(f"  First chunk page: {chunks[0]['page']}")
            print(f"  ✓ Data structure looks good!")
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nContract Manager is ready for multi-airline use!")
        
    except Exception as e:
        print(f"\n✗ Error loading NAC: {e}")
        print("\nPlease check that all files are in the correct location.")