from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, Http404
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator 
from django.db.models import Q
from django.forms import modelformset_factory
from django.http import HttpResponse, HttpResponseRedirect


# Create your views here.
# from django.contrib.staticfiles
from .forms import (
						CheckoutForm, CouponForm, 
						RefundForm, PostForms,
						ImageForms,CantactForms
					)
from .mpesa import Mpesaform
from .models import (
				Item, OrderItem,
				Order, BillingAddress, 
				Payment, Mpesapay,
				Coupon,Refund, Category,
				Images, Contact

			)
import stripe
import base64
import requests
import ssl
import json
from requests.auth import HTTPBasicAuth
import datetime
import random
import string

stripe.api_key = "pk_test_B471oTONAVuayztFhrOFhxqD00vmj5u5c9"

def post_create(request):
	"""
	Methods creates the Posts
	"""
	if not request.user.is_staff or not request.user.is_superuser:
		raise Http404
	ImageFormSet = modelformset_factory(Images, form=ImageForms, extra=3)
	form  = PostForms(request.POST or None, request.FILES or None)
	formset = ImageFormSet(request.POST or None, request.FILES or None,
													queryset=Images.objects.none())
	if form.is_valid() and formset.is_valid():
		instance = form.save(commit=False)
		instance.user = request.user
		instance.save()
		# message success
		for fx in formset.cleaned_data:
			image = fx['image']
			photo = Images(item=instance, image=image)
			photo.save()
		messages.success(request, "Successfully Created")
		return HttpResponseRedirect(instance.get_absolete_url())
	else:
		messages.error(request, "Not Successfully Created")
		form = PostForms()
	context = {
		"form": form,
		"formset": formset,
	}
	return render(request, "post_form.html", context)

def create_ref_code():
	return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

def products(request, slug):
	instance = get_object_or_404(Item, slug=slug)
	querySet_list = Item.objects.all()
	# def get_queryset(self):
	# show = get_object_or_404(Item, category = slug)
	category = get_object_or_404(Category, slug=slug)
	# category = Category.objects.get(pk=pk)
	show = Item.objects.filter(category=category)
	# show = Item.filter(category=category)
	# Model.objects.get(field_name=some_param)

	context = {
		'items': Item.objects.all(),
		# "title": instance.title,
		# "item": item,
		"instance":instance,
		"category": category,
		"querySet_list": querySet_list,
		"show": show,
	}
	return render(request, "product.html", context)

def list_category(request, slug):
	categories = Category.objects.all()
	if slug:
		category = get_object_or_404(Category, slug=slug)
		item = Item.objects.filter(category=category)
		
	context = {
		'categories': categories,
		'category': category,
		'item':item,
	}
	return render(request, "category.html", context)


class CheckoutView(View):
	def get(self, *args, **kwargs):
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			form = CheckoutForm()
			context = {
				'form': form,
				'couponform': CouponForm(),
				'order': order,
				'DISPLAY_COUPON_FORM':True

			}
			return render(self.request, "checkout.html", context)
		except ObjectDoesNotExist:
			messages.info(self.request, "You do not have an active oredr")
			return redirect("shops:checkout")

	def post(self, *args, **kwargs):
		form = CheckoutForm(self.request.POST or None)
		# Check if user have an order
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			if form.is_valid():
				street_address = form.cleaned_data.get('street_address')
				apartment_address = form.cleaned_data.get('apartment_address')
				county = form.cleaned_data.get('county')
				phone = form.cleaned_data.get('phone')
				zip = form.cleaned_data.get('zip')

				# TODO: Functionality for these field
				# same_shippin_address = form.cleaned_data.get(
				# 	'same_shippin_address')
				# save_info = form.cleaned_data.get('save_info')
				payment_option = form.cleaned_data.get('payment_option')
				billing_address = BillingAddress(
					user=self.request.user,
					street_address=street_address,
					apartment_address=apartment_address,
					county=county,
					phone=phone,
					zip=zip
				)
				billing_address.save()
				order.billing_address = billing_address
				order.save()
				# TODO: add redirect to the selected payment option

				if payment_option == 'S':
					return redirect('shops:payment', payment_option='mpesa')
				elif payment_option == 'M':
					return redirect('shops:mpesapay', payment_option='mpesa')
				else:
					messages.warning(self.request, "Invalid payment selected")
					return redirect('shops:checkout')
		except ObjectDoesNotExist:
			messages.error(self.request, "You do not have an active order")
			return redirect("shops:order-summary")

class PaymentView(View):
	def get(self, *args, **kwargs):

		return render(self.request, "payment.html")

def about(request):
	return render(request, "about.html")

def contact(request):
	form = CantactForms(request.POST or None)
	if form.is_valid():
		instance = form.save(commit=False)
		instance.save()
		messages.success(request, "Successfully Created")
	content = {
		'form': form,
	}
	return render(request, "contact.html", content)



def services(request):
	object_list = Item.objects.all().order_by("-timestamp")
	query = request.GET.get("q")
	if query:
		object_list = object_list.filter(
			Q(title__icontains=query) | 
			Q(description__icontains=query)|
			Q(price__icontains=query)|
			Q(slug__icontains=query)
			).distinct()
	paginator = Paginator(object_list, 6)
	page = request.GET.get('page')
	querySet = paginator.get_page(page)

	context = {
		"object_list":querySet,
	}

	return render (request, "service.html", context)

def home(request):
	today = timezone.now().date()

	object_list = Item.objects.all().order_by("-timestamp")
	query = request.GET.get("q")
	if query:
		object_list = object_list.filter(
			Q(title__icontains=query) | 
			Q(description__icontains=query)|
			Q(price__icontains=query)|
			Q(slug__icontains=query)
			).distinct()
	paginator = Paginator(object_list, 6)
	page = request.GET.get('page')
	querySet = paginator.get_page(page)

	# Trouser 
	w = Category.objects.get(name = 'Trouser')
	cat = Item.objects.filter(category=w).order_by('-title')[:6]
	
	# # get link Trouser categories
	get_link = Category.objects.get(name = 'Trouser')
	link = Item.objects.filter(category=get_link)[:1]

	# # Shoes Collections
	shoes = Category.objects.get(name = 'Shoes')
	shoes_cat = Item.objects.filter(category=shoes).order_by('-title')[:6]
	
	# get link shoes categories
	# get_link_shoes = Category.objects.get(name = 'Shoes')
	# linkshoes = Item.objects.filter(category=get_link_shoes)[:1]

	# Tops Collections
	# tops = Category.objects.get(name = 'Tops')
	# tops_cat = Item.objects.filter(category=tops).order_by('-title')[:6]


	# # Get link tops cotegories
	# get_link_tops = Category.objects.get(name = 'Tops')
	# tops_cat_link = Item.objects.filter(category=get_link_tops)[:1]

	context = {
		'object_list': querySet,
		# 'cat':cat,
		'shoes_cat':shoes_cat,
		# 'tops_cat': tops_cat,
		# 'link': link,
		# # 'linkshoes':linkshoes,
		# 'tops_cat_link':tops_cat_link,
		# 'today':today
		}
	return render(request, "home.html", context)

# All New Products
def Newproduct(request):
	object_list = Item.objects.all().order_by("-timestamp")
	query = request.GET.get("q")
	if query:
		object_list = object_list.filter(
			Q(title__icontains=query) | 
			Q(description__icontains=query)|
			Q(price__icontains=query)|
			Q(slug__icontains=query)
			).distinct()
	paginator = Paginator(object_list, 12)
	page = request.GET.get('page')
	querySet = paginator.get_page(page)

	context = {
		'newproduct': querySet
	}
	return render(request, "new.html", context)

class Mpesa(View):
	def get(self, *args, **kwargs):
		form = Mpesaform()
		order = Order.objects.get(user=self.request.user, ordered=False)
		context = {
			'order': order,
			'form': form
		}
		return render(self.request, "mpesapay.html", context)

	def post(self, *args, **kwargs):
		form = Mpesaform(self.request.POST or None)
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			amount = int(order.get_total())
			print(amount)
			if form.is_valid():
				phone = form.cleaned_data.get('phone')

				pay_bills = Mpesapay(
					user = self.request.user,
					phone=phone,
					amount=amount,
				)
				pay_bills.save()
				
				# Lipa na mpesa Functionality 
				consumer_key = "EKyBEUXldtz0pAlmfv6fDELROh5vwQH0"
				consumer_secret = "KADx7lxZWJdU0TcW"

				# api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" #AUTH URL
				api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

				r = requests.get(api_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))

				data = r.json()
				access_token = "Bearer" + ' ' + data['access_token']

				#GETTING THE PASSWORD
				timestamp = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
				passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
				business_short_code = "174379"
				data = business_short_code + passkey + timestamp
				encoded = base64.b64encode(data.encode())
				password = encoded.decode('utf-8')
				# BODY OR PAYLOAD
				payload = {
				    "BusinessShortCode": business_short_code,
				    "Password": password,
				    "Timestamp": timestamp,
				    "TransactionType": "CustomerPayBillOnline",
				    "Amount": amount,
				    "PartyA": phone,
				    "PartyB": business_short_code,
				    "PhoneNumber": phone,
				    "CallBackURL": "https://senditparcel.herokuapp.com/api/v2/callback",
				    "AccountReference": "account",
				    "TransactionDesc": "account"
				}

				#POPULAING THE HTTP HEADER
				headers = {
				    "Authorization": access_token,
				    "Content-Type": "application/json"
				}
				url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest" #C2B URL
				response = requests.post(url, json=payload, headers=headers)
				print (response.text)
				# return {"message": 'Wait Response on Your phone'}
				messages.success(self.request, "Wait Response on Your phone")
				return redirect("/")
		except ObjectDoesNotExist:
			messages.error(self.request, "You do not have an active order")
			return redirect("shops:order-summary")

class PaymentViews(View):
	def get(self, *args, **kwargs):
		order = Order.objects.get(user=self.request.user, ordered=False)
		if order.billing_address:
			context = {
				'order': order,
				'DISPLAY_COUPON_FORM':False
			}
			return render(self.request, "payment.html", context)
		else:
			messages.warning(
				self.request, "You have not added a billing address")
			return redirect("shops:checkout")

	def post(self, *args, **kwargs):
		order = Order.objects.get(user=self.request.user, ordered=False)
		token = self.request.POST.get('stripeToken')
		amount = int(order.get_total() * 100)
		try:
			charge = stripe.Charge.create(
			  amount=amount, #cents
			  currency="usd",
			  source=token, # obtained with Stripe.js
			  idempotency_key='PtJwqzZri2xry7MQ',
			)
			# Create the payement
			payement = Payment()
			payment.stipe_change_id = charge['id']
			payment.user = self.request.user
			payment.amount = order.get_total()
			payment.save()

			order_items = order.items.all()
			order_items.update(ordered=True)
			for item in order_items:
				item.save()

			# assign the payment to the Order
			order.ordered = True
			order.payment = payment
			order.ref_code = create_ref_code()
			order.save()

			messages.success(self.request, "Your order was successfull")
			return redirect("/")

		except stripe.error.CardError as e:
			body = e.json_body
			err = body.get('error', {})
			# messages.error(self.request, f"{err.get('message')}")
			message.error(self.request, "%s" %(err.get('message')))
			return redirect("/")

		except stripe.error.RateLimitError as e:
		  # Too many requests made to the API too quickly
		  messages.error(self.request, "Rate limit error")
		  return redirect("/")

		except stripe.error.InvalidRequestError as e:
		  # Invalid parameters were supplied to Stripe's API
		  messages.error(self.request, "Invalid parameters")
		  return redirect("/")

		except stripe.error.AuthenticationError as e:
		  # Authentication with Stripe's API failed
		  # (maybe you changed API keys recently)
		  messages.error(self.request, "Not authenticated")
		  return redirect("/")

		except stripe.error.APIConnectionError as e:
		  # Network communication with Stripe failed
		  messages.error(self.request, "Network Error")
		  return redirect("/")
		except stripe.error.StripeError as e:
		  # Display a very generic error to the user, and maybe send
		  # yourself an email
		  messages.error(self.request, "Something went wrong. you were not charged. Please try again")
		  return redirect("/")
		except Exception as e:
		  # Something else happened, completely unrelated to Stripe
		  # Send an email to ourselves
		  messages.error(self.request, "A serious error occurred. We have been notified")
		  return redirect("/")


# Summary Orders
@method_decorator(login_required, name='dispatch')
# @login_required
class OrderSummaryView(LoginRequiredMixin, View):
	def get(self, *args, **kwargs):
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			context = {
				'object': order
			}
			return render(self.request, 'order_summary.html', context)
		except ObjectDoesNotExist:
			messages.error(self.request, "You do not have an active order")
			return redirect("/")

class ItemDetailView(DetailView):
	model = Item
	template_name = "product.html"


@login_required
def add_to_cart(request, slug):
	item = get_object_or_404(Item, slug=slug)
	order_item, created = OrderItem.objects.get_or_create(
		item=item,
		user=request.user,
		ordered=False
	)
	order_qs = Order.objects.filter(user=request.user, ordered=False)
	if order_qs.exists():
		order = order_qs[0]

		# check if the order item is in the order
		if order.items.filter(item__slug=item.slug).exists():
			order_item.quantity += 1 
			order_item.save()
			messages.info(request, "This item quantity was updated")
			return redirect("shops:order-summary")
		else:
			order.items.add(order_item)
			messages.info(request, "This item was added to your cart.")
			return redirect("shops:order-summary")			
	else:
		ordered_date = timezone.now()
		order = Order.objects.create(
			user=request.user, ordered_date=ordered_date)
		order.items.add(order_item)
		messages.info(request, "This item was added to your cart")
	return redirect("shops:order-summary")


@login_required
def remove_from_cart(request, slug):
	item = get_object_or_404(Item, slug=slug)
	# Check if user has orders
	order_qs = Order.objects.filter(
		user=request.user,
		ordered=False
	)
	if order_qs.exists():
		order = order_qs[0]

		if order.items.filter(item__slug=item.slug).exists():
			order_item = OrderItem.objects.filter(
				item=item,
				user=request.user,
				ordered=False
			)[0]
			order.items.remove(order_item)
			messages.info(request, "This Item was removed from cart")
			return redirect("shops:order-summary")
		else:
			messages.info(request, "This was not in Cart")
			return redirect("shops:product", slug=slug)			
	else:
		messages.info(request, "You do not have an active order")
		return redirect("shops:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
	# Check if the order exists
	item = get_object_or_404(Item, slug=slug)
	# Check if user has orders
	order_qs = Order.objects.filter(
		user=request.user,
		ordered=False
	)
	if order_qs.exists():
		order = order_qs[0]

		if order.items.filter(item__slug=item.slug).exists():
			order_item = OrderItem.objects.filter(
				item=item,
				user=request.user,
				ordered=False
			)[0]
			if order_item.quantity > 1:
				order_item.quantity -= 1 
				order_item.save()
			else:
				order.items.remove(order_item)
			messages.info(request, "This Item quantity was updated")
			return redirect("shops:order-summary")
		else:
			messages.info(request, "This was not in Cart")
			return redirect("shops:product", slug=slug)			
	else:
		messages.info(request, "You do not have an active order")
		return redirect("shops:product", slug=slug)


def get_coupon(request, code):
	try:
		coupon = Coupon.objects.get(code=code)
		return coupon
	except ObjectDoesNotExist:
		messages.info(request, "This coupon does not exist")
		return redirect("shops:checkout")



class AddCouponView(View):
	def post(self, *args, **kwargs):
		form = CouponForm(self.request.POST or None)
		if form.is_valid():
			try:
				code = form.cleaned_data.get('code')
				order = Order.objects.get(
        	user=self.request.user, ordered=False)
				order.coupon = get_coupon(self.request, code)
				order.save()
				messages.success(self.request, "Successfully added coupon")
				return redirect("shops:checkout")
			except ObjectDoesNotExist:
				messages.info(self.request, "You do not have an active order")
		return redirect("shops:checkout")

class RequestRefundView(View):
	def get(self, *args, **kwargs):
		form = RefundForm()
		context = {
			'form': form
		}
		return render(self.request, "request_refund.html", context)

	def post(self, *args, **kwargs):
		form = RefundForm(self.request.POST or None)
		if form.is_valid():
			ref_code = form.cleaned_data.get('ref_code')
			message = form.cleaned_data.get('message')
			email = form.cleaned_data.get('email')
			# edit the order
			try:
				order = Order.objects.get(ref_code=ref_code)
				order.refund_requested = True
				order.save()

				# store the refund
				refund = Refund()
				refund.order = order
				refund.reason = message
				refund.email = email
				refund.save()

				messages.info(self.request, "You request was received")
				return redirect("shops:request-refund")
			except ObjectDoesNotExist:
				messages.info(self.request, "This order does not exit.")
				return redirect("shops:request-refund")

