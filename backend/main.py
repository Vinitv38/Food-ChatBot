from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
import db_helper
import generic_helper

app = FastAPI()
inprogress_orders={}
empty ={}

@app.post('/')
async def handle_request(request: Request):

    payload= await request.json()

    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']

    session_id = generic_helper.extract_session_id(output_contexts[0]['name'])
    

    intent_handler_dict = {
        'order.add - context: ongoing-order': add_to_order,
        'order.remove - context:ongoing-order': remove_from_order,
        'order.complete - context: ongoing-order': complete_order,
        'track.order - context:ongoing-tracking': track_order ,
    }

    return intent_handler_dict[intent](parameters, session_id)


def add_to_order(parameters: dict, session_id: str):
    food_items = parameters["food-item"]
    quantities = parameters["number"]

    if len(food_items) != len(quantities):
        fulfillmentText = "Sorry I didn't understand. Please specify food items and there quantity clearly."
    else: 
        new_food_dict = dict(zip(food_items, quantities)) 
        if session_id in inprogress_orders:
            current_food_dict = inprogress_orders[session_id]
            current_food_dict.update(new_food_dict)
            inprogress_orders[session_id] = current_food_dict
        else:
            inprogress_orders[session_id] = new_food_dict

        print("********************************")
        print(inprogress_orders)    

        order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillmentText = f"so far you have {order_str}, would you like anything else ?"

    return JSONResponse(content={
        "fulfillmentText": fulfillmentText
    })
# inprogress_orders ={
#     'session_id_1':{"pizza":2, "samosa":1}
# }
def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        fulfillmentText="I'm having trouble finding your order. Sorry! can you place new order."
    else:
        order = inprogress_orders[session_id]
        order_id = save_to_db(order)


        if order_id == -1:
            fulfillmentText="Sorry, I coundnt place your order due to backend error. "\
                            "Please place a new order again"
        else:
            order_total = db_helper.get_total_order_price(order_id)

            fulfillmentText = f"Awesome. We have placed your order. "\
                              f"Your order id is {order_id}. "\
                              f"Your order total is {order_total} which you can pay at the time of delivery."
            
        del inprogress_orders[session_id]
            
    return JSONResponse(content={
        "fulfillmentText":fulfillmentText
    })

def save_to_db(order:dict):

    next_order_id = db_helper.get_next_order_id()
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )


        if rcode == -1:
            return -1
        
    db_helper.insert_order_tracking(next_order_id, "in progress")
    return next_order_id

def remove_from_order(parameters: dict, session_id: str):
    food_item = parameters["food-item"][0]
    if session_id in inprogress_orders:
        current_food_dict = inprogress_orders[session_id]
        if food_item in current_food_dict.keys():
            current_food_dict.pop(food_item)
            inprogress_orders[session_id] = current_food_dict
            

            order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
            if order_str == '':
                fulfillmentText = "You have an empty cart till now, please place an order using 'Place a new order' command"
            else:       
                fulfillmentText = f"so far you have {order_str}, would you like anything else ?"
        else:
            fulfillmentText = f"Sorry, I can't find {food_item} in your order."
    else:
        fulfillmentText = "You have an empty cart till now, please place an order using 'Place a new order' command"

    print("********************************")
    print(inprogress_orders)    

    

    return JSONResponse(content={
        "fulfillmentText": fulfillmentText
    })


def track_order(parameters: dict, session_id):
    order_id =int( parameters['order_id'])
    order_status = db_helper.get_order_status(order_id)
    # order_status = db_helper.get_order_status(order_id)

    if order_status:
        fulfillmentText= f"The order status for order id {order_id} is: {order_status}"
    else:
        fulfillmentText= f"No order found with order id {order_id}"

    return JSONResponse(content={
        "fulfillmentText": fulfillmentText
    })