from goldenverba.server.types import QueryPayload
from goldenverba.verba_manager import VerbaManager

if __name__ == '__main__':
    verba_manager = VerbaManager()

    client = verba_manager.client
    if client is None:
        print('client is None')
        exit(0)

    chunks, ctx = verba_manager.retrieve_chunks([QueryPayload(query='chuj', doc_label='marks-swift/#')])
    print([{'type': r.doc_type, 'score': r.score, 'tl': len(r.text), 'did': r.doc_uuid} for r in chunks])

    print(verba_manager.retrieve_document('f3887b02-6d54-4032-9771-4b57ad860bac'))
