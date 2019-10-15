import datetime
from sqlalchemy.dialects.postgresql import JSON
from flask import current_app
from sqlalchemy.ext.hybrid import hybrid_property

from server import db
from server.models.utils import ModelBase, ManyOrgBase
from server.models.models import Token
from server.exceptions import (
    NoTransferAccountError,
    UserNotFoundError
)
from server.utils.blockchain_tasks import (
    make_token_transfer,
    get_blockchain_task
)
from server.utils.transfer_enums import TransferTypeEnum, TransferStatusEnum, TransferModeEnum

class CreditTransfer(ManyOrgBase, ModelBase):
    __tablename__ = 'credit_transfer'

    uuid            = db.Column(db.String, unique=True)

    resolved_date   = db.Column(db.DateTime)
    transfer_amount = db.Column(db.Integer)

    transfer_type   = db.Column(db.Enum(TransferTypeEnum))
    transfer_status = db.Column(db.Enum(TransferStatusEnum), default=TransferStatusEnum.PENDING)
    transfer_mode   = db.Column(db.Enum(TransferModeEnum))
    transfer_use    = db.Column(JSON)

    resolution_message = db.Column(db.String())

    blockchain_task_id = db.Column(db.Integer)

    token_id        = db.Column(db.Integer, db.ForeignKey(Token.id))

    sender_transfer_account_id       = db.Column(db.Integer, db.ForeignKey("transfer_account.id"))
    recipient_transfer_account_id    = db.Column(db.Integer, db.ForeignKey("transfer_account.id"))

    sender_blockchain_address_id    = db.Column(db.Integer, db.ForeignKey("blockchain_address.id"))
    recipient_blockchain_address_id = db.Column(db.Integer, db.ForeignKey("blockchain_address.id"))

    sender_user_id    = db.Column(db.Integer, db.ForeignKey("user.id"))
    recipient_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    blockchain_transactions = db.relationship('BlockchainTransaction', backref='credit_transfer', lazy=True)

    attached_images = db.relationship('UploadedImage', backref='credit_transfer', lazy=True)

    @hybrid_property
    def blockchain_status(self):
        if self.blockchain_task_id:
            task = get_blockchain_task(self.blockchain_task_id)

            return task.get('status', 'ERROR')
        else:
            return 'UNKNOWN'

        # if len(self.uncompleted_blockchain_tasks) == 0:
        #     return 'COMPLETE'
        #
        # if len(self.pending_blockchain_tasks) > 0:
        #     return 'PENDING'
        #
        # if len(self.failed_blockchain_tasks) > 0:
        #     return 'ERROR'
        #
        # return 'UNKNOWN'


    @hybrid_property
    def blockchain_status_breakdown(self):

        required_task_dict = {x: {'status': 'UNKNOWN', 'hash': None} for x in self._get_required_blockchain_tasks()}

        for transaction in self.blockchain_transactions:
            status_hierarchy = ['UNKNOWN', 'FAILED', 'PENDING', 'SUCCESS']
            task_type = transaction.transaction_type

            current_status = required_task_dict.get(task_type).get('status')
            proposed_new_status = transaction.status

            try:
                if current_status and status_hierarchy.index(proposed_new_status) > status_hierarchy.index(current_status):
                    required_task_dict[task_type]['status'] = proposed_new_status
                    required_task_dict[task_type]['hash'] = transaction.hash
            except ValueError:
                pass

        return required_task_dict

    @hybrid_property
    def pending_blockchain_tasks(self):
        return self._find_blockchain_tasks_with_status_of('PENDING')

    @hybrid_property
    def failed_blockchain_tasks(self):
        return self._find_blockchain_tasks_with_status_of('FAILED')

    @hybrid_property
    def uncompleted_blockchain_tasks(self):
        required_task_set = set(self._get_required_blockchain_tasks())
        completed_task_set = self._find_blockchain_tasks_with_status_of('SUCCESS')
        return required_task_set - completed_task_set

    def _get_required_blockchain_tasks(self):
        if self.transfer_type == TransferTypeEnum.DISBURSEMENT and not current_app.config['IS_USING_BITCOIN']:

            if current_app.config['USING_EXTERNAL_ERC20']:
                master_wallet_approval_status = self.recipient_transfer_account.master_wallet_approval_status

                if (master_wallet_approval_status in ['APPROVED', 'NOT_REQUIRED']
                        and float(current_app.config['FORCE_ETH_DISBURSEMENT_AMOUNT']) <= 0):

                    required_tasks = ['disbursement']

                elif master_wallet_approval_status in ['APPROVED', 'NOT_REQUIRED']:

                    required_tasks = ['disbursement', 'ether load']

                else:
                    required_tasks = ['disbursement', 'ether load', 'master wallet approval']

            else:
                required_tasks = ['initial credit mint']

        else:
            required_tasks = ['transfer']

        return required_tasks

    def _find_blockchain_tasks_with_status_of(self, required_status):
        if required_status not in ['PENDING', 'SUCCESS', 'FAILED']:
            raise Exception('required_status must be one of PENDING, SUCCESS or FAILED')

        completed_task_set = set()
        for transaction in self.blockchain_transactions:
            if transaction.status == required_status:
                completed_task_set.add(transaction.transaction_type)
        return completed_task_set

    def send_blockchain_payload_to_worker(self, is_retry=False):

        sender_approval = self.sender_transfer_account.get_or_create_system_transfer_approval()

        recipient_approval = self.recipient_transfer_account.get_or_create_system_transfer_approval()

        self.blockchain_task_id = make_token_transfer(
            signing_address=self.sender_transfer_account.organisation.system_blockchain_address,
            token=self.token,
            from_address=self.sender_transfer_account.blockchain_address,
            to_address=self.recipient_transfer_account.blockchain_address,
            amount=self.transfer_amount,
            dependent_on_tasks=[
                sender_approval.eth_send_task_id, sender_approval.approval_task_id,
                recipient_approval.eth_send_task_id, recipient_approval.approval_task_id
            ]
        )

    def resolve_as_completed(self, existing_blockchain_txn=None):
        self.resolved_date = datetime.datetime.utcnow()
        self.transfer_status = TransferStatusEnum.COMPLETE

        self.sender_transfer_account.balance -= self.transfer_amount
        self.recipient_transfer_account.balance += self.transfer_amount

        if self.transfer_type == TransferTypeEnum.DISBURSEMENT:
            if self.recipient_user and self.recipient_user.transfer_card:
                self.recipient_user.transfer_card.update_transfer_card()

        if not existing_blockchain_txn:
            self.send_blockchain_payload_to_worker()

    def resolve_as_rejected(self, message=None):
        self.resolved_date = datetime.datetime.utcnow()
        self.transfer_status = TransferStatusEnum.REJECTED

        if message:
            self.resolution_message = message

    def check_sender_has_sufficient_balance(self):
        return self.sender_user and self.sender_transfer_account.balance - self.transfer_amount >= 0

    def check_sender_is_approved(self):
        return self.sender_user and self.sender_transfer_account.is_approved

    def check_recipient_is_approved(self):
        return self.recipient_user and self.recipient_transfer_account.is_approved

    def find_user_transfer_accounts_with_matching_token(self, user, token):
        matching_transfer_accounts = []
        for transfer_account in user.transfer_accounts:
            if transfer_account.token == token:
                matching_transfer_accounts.append(transfer_account)
        if len(matching_transfer_accounts) == 0:
            raise NoTransferAccountError("No transfer account for user {} and token".format(user, token))
        if len(matching_transfer_accounts) > 1:
            raise Exception(f"User has multiple transfer accounts for token {token}")

        return matching_transfer_accounts[0]

    def _select_transfer_account(self, supplied_transfer_account, user, token):
        if token is None:
            raise Exception("Token must be specified")
        if supplied_transfer_account:
            if user is not None and user not in supplied_transfer_account.users:
                raise UserNotFoundError(f'User {user} not found for transfer account {supplied_transfer_account}')
            return supplied_transfer_account

        return self.find_user_transfer_accounts_with_matching_token(user, token)

    def append_organisation_if_required(self, organisation):
        if organisation not in self.organisations:
            self.organisations.append(organisation)

    def __init__(self,
                 amount,
                 token=None,
                 sender_user=None,
                 recipient_user=None,
                 sender_transfer_account=None,
                 recipient_transfer_account=None,
                 transfer_type=None, uuid=None):

        self.transfer_amount = amount

        self.sender_user = sender_user
        self.recipient_user = recipient_user

        self.sender_transfer_account = sender_transfer_account or self._select_transfer_account(
            sender_transfer_account, sender_user, token)

        self.token = token or self.sender_transfer_account.token

        self.recipient_transfer_account = recipient_transfer_account or self._select_transfer_account(
            recipient_transfer_account, recipient_user, self.token)

        if self.sender_transfer_account.token != self.recipient_transfer_account.token:
            raise Exception("Tokens do not match")

        self.transfer_type = transfer_type

        if uuid is not None:
            self.uuid = uuid

        self.append_organisation_if_required(self.recipient_transfer_account.organisation)
        self.append_organisation_if_required(self.sender_transfer_account.organisation)

class BlockchainTransaction(ModelBase):
    __tablename__ = 'blockchain_transaction'

    status = db.Column(db.String)  # PENDING, SUCCESS, FAILED
    message = db.Column(db.String)
    block = db.Column(db.Integer)
    submitted_date = db.Column(db.DateTime)
    added_date = db.Column(db.DateTime)
    hash = db.Column(db.String)
    nonce = db.Column(db.Integer)
    transaction_type = db.Column(db.String)

    is_bitcoin = db.Column(db.Boolean)

    # Output spent txn for bitcoin
    has_output_txn = db.Column(db.Boolean, default=False)

    credit_transfer_id = db.Column(db.Integer, db.ForeignKey(CreditTransfer.id))

    signing_blockchain_address_id = db.Column(db.Integer, db.ForeignKey('blockchain_address.id'))